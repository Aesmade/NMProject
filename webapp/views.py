from django.shortcuts import render
from django.http.response import HttpResponse
from django.views.generic import ListView
from models import *
from django.db import transaction
from chartit import DataPool, Chart
import django.utils.timezone
import django.core.exceptions
import django.db.models
import math
import datetime
import time


class UTC0030(datetime.tzinfo):
    _offset = datetime.timedelta(hours=3)
    _dst = datetime.timedelta(0)
    _name = "+0030"

    def utcoffset(self, dt):
        return self.__class__._offset

    def dst(self, dt):
        return self.__class__._dst

    def tzname(self, dt):
        return self.__class__._name


class UserList(ListView):
    queryset = BatteryStatus.objects.values("email").distinct()
    template_name = "webapp/select.html"

    def get_context_data(self, **kwargs):
        context = super(ListView, self).get_context_data(**kwargs)
        context['curdate'] = datetime.datetime.now()
        return context


def index(request):
    return HttpResponse("hello world")


def saveobjects(data, name):
    nametoobj = {"bsobjects": BaseStation, "batteryobjects": BatteryStatus, "gpsobjects": GPSStatus,
                 "wifiobjects": WifiStatus}
    if name not in nametoobj:
        return
    print "Updating " + name
    objtype = nametoobj[name]
    iterdata = iter(data)
    objtype.objects.all().delete()
    next(iterdata)
    with transaction.atomic():
        for line in iterdata:
            if line[-1] == '\n':
                line = line[:-1]
            data = line.split("\t")
            try:
                obj = objtype()
                obj.setdata(data)
                obj.save()
            except django.core.exceptions.ValidationError:
                print "Validation error"
            except IndexError:
                print "Out of array range"


def upload(request):
    uploaded = False
    if request.method == "POST":
        for key, val in request.FILES.iteritems():
            saveobjects(val, key)
            uploaded = True
            if key == "wifiobjects":
                wmap = dict({})
                for w in WifiStatus.objects.all():
                    if w.bssid not in wmap:
                        wmap[w.bssid] = (w.ssid, [(math.pow(10, float(w.level) / 10), w.latitude * math.pi / 180,
                                                   w.longitude * math.pi / 180)])
                    else:
                        wmap[w.bssid][1].append((math.pow(10, float(w.level) / 10), w.latitude * math.pi / 180,
                                                 w.longitude * math.pi / 180))
                with transaction.atomic():
                    for wkey, wval in wmap.iteritems():
                        lat = 0
                        lon = 0
                        totalw = 0
                        for i in wval[1]:
                            if i[1] != -1.0 and i[2] != -1.0:
                                lat += i[0] * i[1]
                                lon += i[0] * i[2]
                                totalw += i[0]
                        try:
                            wp = WifiPos(bssid=wkey, ssid=wval[0], latitude=(lat / totalw) * 180 / math.pi,
                                         longitude=(lon / totalw) * 180 / math.pi)
                            wp.save()
                            wsset = WifiStatus.objects.filter(bssid=wkey)
                            wsset.update(realpos=wp)
                            #wsset.save()
                        except ZeroDivisionError:
                            print "Error finding access point position"
    return render(request, "webapp/upload.html", {"uploadsucc": uploaded})


def show(request):
    u = request.POST.get("user", "")
    strstart = request.POST.get("start", "01/01/1990")
    strend = request.POST.get("end", "01/01/2100")
    sdate = datetime.datetime(*time.strptime(strstart, "%d/%m/%Y")[:3], tzinfo=UTC0030())
    edate = datetime.datetime(*time.strptime(strend, "%d/%m/%Y")[:3], tzinfo=UTC0030())
    wifires = WifiStatus.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate)
    wifires = wifires.values("ssid", "bssid", "realpos__latitude", "realpos__longitude", "frequency").\
        annotate(RSSI=django.db.models.Avg("level"))
    gpsres = GPSStatus.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate).order_by("timestamp")
    bssres = BaseStation.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate)
    bssres = bssres.exclude(latitude=-1.0).exclude(longitude=-1.0)

    sr = BatteryStatus.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate).order_by('timestamp')

    ds = DataPool(
        series=
        [{'options': {
            'source': sr},
          'terms': [
              'timestamp',
              'level']}
        ])

    cht = Chart(
        datasource=ds,
        series_options=
        [{'options': {
            'type': 'area',
            'stacking': False},
          'terms': {
              'timestamp': [
                  'level']
          }}],
        chart_options=
        {'title': {
            'text': 'Battery level'},
         'xAxis': {
             'title': {
                 'text': 'Timestamp'}},
         'yAxis': {'max': 100}},
        x_sortf_mapf_mts=(None, lambda i: i.astimezone(UTC0030()).strftime("%d-%m-%y %H:%M"), False))

    return render(request, "webapp/show1st.html", {"wifi": wifires, "gps": gpsres, "bss": bssres, "chart": cht})


def centroid(points):
    if len(points) == 0:
        return 0.0, 0.0
    lats = [x.latitude for x in points]
    lons = [x.longitude for x in points]
    return sum(lats)/len(lats), sum(lons)/len(lons)


def find_stay_points(points, dmax, tmin, tmax):
    lsp = []
    i = 0
    while i < len(points)-1:
        for j in range(i+1, len(points)):
            if points[j].timestamp-points[j-1].timestamp > tmax:
                if points[j-1].timestamp-points[i].timestamp > tmin:
                    lsp.append(centroid(points[i:j]))
                i = j
                break
            elif (points[i].latitude-points[j].latitude)**2 + (points[i].longitude-points[j].longitude)**2 > dmax:
                if points[j-1].timestamp-points[i].timestamp > tmin:
                    lsp.append(centroid(points[i:j]))
                    i = j
                    break
                i += 1
                break
            elif j == len(points)-1:
                if points[j].timestamp-points[i].timestamp > tmin:
                    lsp.append(centroid(points[i:j+1]))
                i = j
                break
    return lsp


def stay(request):
    u = request.POST.get("user", "")
    strstart = request.POST.get("start", "01/01/1990")
    strend = request.POST.get("end", "01/01/2100")
    try:
        sdate = datetime.datetime(*time.strptime(strstart, "%d/%m/%Y")[:3], tzinfo=UTC0030())
        edate = datetime.datetime(*time.strptime(strend, "%d/%m/%Y")[:3], tzinfo=UTC0030())
        dmax = int(request.POST.get("dmax", 10))**2
        tmin = datetime.timedelta(hours=int(request.POST.get("tmin", 10)))
        tmax = datetime.timedelta(hours=int(request.POST.get("tmax", 10)))
    except ValueError:
        return HttpResponse("Only numbers allowed!")
    print dmax, tmin, tmax, sdate, edate
    points = GPSStatus.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate).order_by("timestamp")
    lsp = find_stay_points(points, dmax, tmin, tmax)
    return render(request, "webapp/staypoints.html", {"lsp": lsp})