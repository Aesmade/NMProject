from django.shortcuts import render
from django.http.response import HttpResponse
from django.views.generic import ListView
from django.db.models import Count
from django.db.models.functions import Lower
from models import *
from django.db import transaction
from sklearn.cluster import DBSCAN
import django.db.models
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
        context['olddate'] = datetime.datetime(year=2015, month=1, day=1)
        return context


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

    data = map(lambda i: [i.timestamp.astimezone(UTC0030()).strftime("%d-%m-%y %H:%M"), i.level], sr)

    return render(request, "webapp/tracking.html", {"wifi": wifires, "gps": gpsres, "bss": bssres, "data": data})


def centroid(points):
    if len(points) == 0:
        return 0.0, 0.0, 0, 0
    lats = [x.latitude for x in points]
    lons = [x.longitude for x in points]
    return sum(lats)/len(lats), sum(lons)/len(lons), points[0].timestamp, points[-1].timestamp


def clusterarea(points):
    z = zip(*points)
    lats = z[0]
    lons = z[1]
    return sum(lats)/len(lats), sum(lons)/len(lons), min(lats), min(lons), max(lats), max(lons)


def haversine(p1, p2):
    #haversine formula - find distance between two (lat, long) pairs
    r = 6371000
    f1 = p1.latitude * math.pi / 180
    f2 = p2.latitude * math.pi / 180
    df = (p1.latitude-p2.latitude) * math.pi / 180
    dl = (p1.longitude-p2.longitude) * math.pi / 180
    a = math.sin(df/2)**2 + math.cos(f1)*math.cos(f2)*math.sin(dl/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return r*c


def find_stay_points(points, dmax, tmin, tmax):
    lsp = []
    i = 0
    n = len(points)
    while i < n-1:
        for j in range(i+1, n):
            if points[j].timestamp-points[j-1].timestamp > tmax:
                if points[j-1].timestamp-points[i].timestamp > tmin:
                    lsp.append(centroid(points[i:j]))
                i = j
                break
            elif haversine(points[i], points[j]) > dmax:
                if points[j-1].timestamp-points[i].timestamp > tmin:
                    lsp.append(centroid(points[i:j]))
                    i = j
                    break
                i += 1
                break
            elif j == n-1:
                if points[j].timestamp-points[i].timestamp > tmin:
                    lsp.append(centroid(points[i:]))
                i = j
                break
    return lsp


def stay(request):
    strstart = request.POST.get("start", "01/01/1990")
    strend = request.POST.get("end", "01/01/2100")
    try:
        sdate = datetime.datetime(*time.strptime(strstart, "%d/%m/%Y")[:3], tzinfo=UTC0030())
        edate = datetime.datetime(*time.strptime(strend, "%d/%m/%Y")[:3], tzinfo=UTC0030())
        dmax = int(request.POST.get("dmax", 10))
        tmin = datetime.timedelta(hours=int(request.POST.get("tmin", 10)))
        tmax = datetime.timedelta(hours=int(request.POST.get("tmax", 10)))
    except ValueError:
        return HttpResponse("Only numbers allowed!")
    if "stay" in request.POST:
        u = request.POST.get("user", "")
        points = GPSStatus.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate).order_by("timestamp")
        lsp = find_stay_points(points, dmax, tmin, tmax)
        if len(lsp) > 0:
            return render(request, "webapp/staypoints.html", {"lsp": lsp})
        else:
            return HttpResponse("No stay points found")
    elif "poi" in request.POST:
        lsp = []
        for u in GPSStatus.objects.all().values("email").distinct():
            p = GPSStatus.objects.\
                filter(email=u['email'], timestamp__gte=sdate, timestamp__lte=edate).order_by("timestamp")
            lsp += find_stay_points(list(p), dmax, tmin, tmax)
        if len(lsp) > 0:
            try:
                epsv = float(request.POST.get("eps", 0.01))
                minpts = int(request.POST.get("minpts", 5))
            except ValueError:
                return HttpResponse("Only numbers allowed!")
            lsp2 = [(x[0], x[1]) for x in lsp]
            db = DBSCAN(eps=epsv, min_samples=minpts).fit(lsp2)
            clust = [[] for i in range(max(db.labels_) + 1)]
            for i, val in enumerate(db.labels_):
                if val != -1:
                    clust[val].append(lsp2[i])
            areas = [clusterarea(x) for x in clust]
            return render(request, "webapp/clusters.html", {"areas": areas})
        else:
            return HttpResponse("No stay points found")
    else:
        return HttpResponse("No action selected")


def stats(request):
    lowperhour = BatteryStatus.objects.filter(level__lt=15).extra({'hr': "(strftime('%H', timestamp)+3) % 24"}).\
        values('hr').annotate(c=Count('email', distinct=True))
    opdata = BaseStation.objects.values('operator').annotate(num=Count('email', distinct=True))
    opers = {'VODAFONE GR': 0, 'COSMOTE GR': 0}
    for x in opdata:
        key = x['operator'].upper()
        if "VODAFONE" in key or "CU" in key:
            opers['VODAFONE GR'] += x['num']
        elif 'COSMOT' in key or 'COMSOTE' in key:
            opers['COSMOTE GR'] += x['num']
        else:
            opers[key] = x['num']
    srtdata = sorted(opers, reverse=True, key=opers.get)
    print srtdata
    operssrt = [(x, opers[x]) for x in srtdata]
    return render(request, "webapp/stats.html", {"batterychart": lowperhour, "operators": operssrt})