from django.shortcuts import render
from django.http.response import HttpResponse
from django.views.generic import ListView
from django.db.models import Count, Avg
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
    #context is the list of users
    queryset = BatteryStatus.objects.values("email").distinct()
    template_name = "webapp/select.html"

    def get_context_data(self, **kwargs):
        #set 1/1/2015 and current date as the default start and end dates
        context = super(ListView, self).get_context_data(**kwargs)
        context['curdate'] = datetime.datetime.now()
        context['olddate'] = datetime.datetime(year=2015, month=1, day=1)
        return context


def saveobjects(data, name):
    #save one type of file to the database
    nametoobj = {"bsobjects": BaseStation, "batteryobjects": BatteryStatus, "gpsobjects": GPSStatus,
                 "wifiobjects": WifiStatus}
    if name not in nametoobj:
        return
    print "Updating " + name
    objtype = nametoobj[name]
    iterdata = iter(data)
    objtype.objects.all().delete()
    #skip the first line of the file
    next(iterdata)
    with transaction.atomic():
        for line in iterdata:
            if line[-1] == '\n':
                line = line[:-1]
            #split the parameters and pass them to the object's setdata function
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
        #handle uploaded files
        for key, val in request.FILES.iteritems():
            saveobjects(val, key)
            uploaded = True
            #if a wifi file was uploaded, update the averaged wifi positions in the database
            if key == "wifiobjects":
                wmap = dict({})
                #save all the positions found for each access point
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
                        #add all latitudes and longitudes for each AP
                        for i in wval[1]:
                            if i[1] != -1.0 and i[2] != -1.0:
                                lat += i[0] * i[1]
                                lon += i[0] * i[2]
                                totalw += i[0]
                        try:
                            #save the average in the database
                            wp = WifiPos(bssid=wkey, ssid=wval[0], latitude=(lat / totalw) * 180 / math.pi,
                                         longitude=(lon / totalw) * 180 / math.pi)
                            wp.save()
                            wsset = WifiStatus.objects.filter(bssid=wkey)
                            wsset.update(realpos=wp)
                        except ZeroDivisionError:
                            print "Error finding access point position"
    return render(request, "webapp/upload.html", {"uploadsucc": uploaded})


def show(request):
    #get POST parameters
    u = request.POST.get("user", "")
    strstart = request.POST.get("start", "01/01/1990")
    strend = request.POST.get("end", "01/01/2100")
    sdate = datetime.datetime(*time.strptime(strstart, "%d/%m/%Y")[:3], tzinfo=UTC0030())
    edate = datetime.datetime(*time.strptime(strend, "%d/%m/%Y")[:3], tzinfo=UTC0030())
    #filter wifi statuses by date and email
    wifires = WifiStatus.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate)
    wifistats = list(wifires.values("ssid", "bssid", "realpos__latitude", "realpos__longitude", "timestamp"))
    #find average RSSI and frequency for each AP
    avgs = dict([(x['bssid'], (x['RSSI'], x['freq'])) for
                 x in list(wifires.values("bssid").annotate(RSSI=Avg("level"), freq=Avg("frequency")))])
    for i in wifistats:
        i['RSSI'] = avgs[i['bssid']][0]
        i['freq'] = avgs[i['bssid']][1]
    #filter GPS and base station statuses
    gpsres = list(GPSStatus.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate).order_by("timestamp"))
    bssres = BaseStation.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate)
    bssres = bssres.exclude(latitude=-1.0).exclude(longitude=-1.0)
    sr = BatteryStatus.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate).order_by('timestamp')
    #format each date to a string
    data = map(lambda t: [t.timestamp.astimezone(UTC0030()).strftime("%d-%m-%y %H:%M"), t.level], sr)
    #create context from data
    ctx = {"wifi": wifistats, "gps": gpsres, "bss": bssres, "data": data}
    if request.POST.get("bestpath", "") == "on":
        #if the option to find the path with the least battery consumption is set
        bestpath = []
        #for each point visited
        for i in gpsres:
            bestv = -1
            bestt = (0, 0)
            for j in wifistats:
                #check only APs with timestamps less than an hour apart from the current point
                if abs((i.timestamp - j['timestamp']).total_seconds()) > 3600:
                    continue
                #find squared distance of current point to AP
                pdist = (math.cos((i.latitude+j['realpos__latitude'])/2) * (j['realpos__longitude']-i.longitude))**2 + \
                    (j['realpos__latitude']-i.latitude)**2
                #use time difference + RSSI*10 + distance*10000000 as the metric
                cur = abs((i.timestamp - j['timestamp']).total_seconds()) + abs(j['RSSI']) * 10 + pdist*10000000
                #find the best AP
                if bestv == -1 or cur < bestv:
                    bestv = cur
                    bestt = (j['realpos__latitude'], j['realpos__longitude'])
            #if an AP was found, add it to the list
            if bestv != -1 and (len(bestpath) == 0 or bestpath[-1] != bestt):
                bestpath.append(bestt)
        ctx['bestpath'] = bestpath
    return render(request, "webapp/tracking.html", ctx)


def centroid(points):
    #if no points
    if len(points) == 0:
        return 0.0, 0.0, 0, 0
    lats = [x.latitude for x in points]
    lons = [x.longitude for x in points]
    #average points and return first and last timestamp
    return sum(lats)/len(lats), sum(lons)/len(lons), points[0].timestamp, points[-1].timestamp


def clusterarea(points):
    z = zip(*points)
    lats = z[0]
    lons = z[1]
    #average points and return the top-left and bottom-right corners of the cluster area rectangle
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
    #stay points algorithm
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
        #get POST parameters
        sdate = datetime.datetime(*time.strptime(strstart, "%d/%m/%Y")[:3], tzinfo=UTC0030())
        edate = datetime.datetime(*time.strptime(strend, "%d/%m/%Y")[:3], tzinfo=UTC0030())
        dmax = int(request.POST.get("dmax", 10))
        tmin = datetime.timedelta(hours=int(request.POST.get("tmin", 10)))
        tmax = datetime.timedelta(hours=int(request.POST.get("tmax", 10)))
    except ValueError:
        return HttpResponse("Only numbers allowed!")
    if "stay" in request.POST:
        #find stay points
        u = request.POST.get("user", "")
        points = GPSStatus.objects.filter(email=u, timestamp__gte=sdate, timestamp__lte=edate).order_by("timestamp")
        lsp = find_stay_points(points, dmax, tmin, tmax)
        if len(lsp) > 0:
            return render(request, "webapp/staypoints.html", {"lsp": lsp})
        else:
            return HttpResponse("No stay points found")
    elif "poi" in request.POST:
        #find points of interest
        lsp = []
        for u in GPSStatus.objects.all().values("email").distinct():
            #find stay points for each user
            p = GPSStatus.objects.\
                filter(email=u['email'], timestamp__gte=sdate, timestamp__lte=edate).order_by("timestamp")
            lsp += find_stay_points(list(p), dmax, tmin, tmax)
        if len(lsp) > 0:
            try:
                epsv = float(request.POST.get("eps", 0.01))
                minpts = int(request.POST.get("minpts", 5))
            except ValueError:
                return HttpResponse("Only numbers allowed!")
            #use DBSCAN with epsilon and min_samples parameters on the stay points
            lsp2 = [(x[0], x[1]) for x in lsp]
            db = DBSCAN(eps=epsv, min_samples=minpts).fit(lsp2)
            clust = [[] for i in range(max(db.labels_) + 1)]
            #make a list of lists, each containing the stay points belonging to a separate point of interest
            for i, val in enumerate(db.labels_):
                if val != -1:
                    clust[val].append(list(lsp2[i]))
            #make rectangles from the points
            areas = [clusterarea(x) for x in clust]
            ctx = {"areas": areas}
            if request.POST.get("placeaps", "") == "on":
                #find APs in points of interest
                wifipts = []
                for a in areas:
                    wifis = WifiPos.objects.filter(latitude__gte=a[2], longitude__gte=a[3], latitude__lte=a[4],
                                                   longitude__lte=a[5]).annotate(freq=Avg('wifistatus__frequency'))
                    wifipts += wifis.values('ssid', 'latitude', 'longitude', 'freq')
                #find channel of each AP
                for i in wifipts:
                    i['channel'] = int((i['freq'] - 2405)/5)
                ctx['points'] = wifipts
            return render(request, "webapp/clusters.html", ctx)
        else:
            return HttpResponse("No stay points found")
    else:
        return HttpResponse("No action selected")


def stats(request):
    #find how many people had <15% battery per each hour
    lowperhour = BatteryStatus.objects.filter(level__lt=15).extra({'hr': "(strftime('%H', timestamp)+3) % 24"}).\
        values('hr').annotate(c=Count('email', distinct=True))
    #find base station info and group by operator
    opdata = BaseStation.objects.values('operator').annotate(num=Count('email', distinct=True))
    opers = {'VODAFONE GR': 0, 'COSMOTE GR': 0}
    for x in opdata:
        key = x['operator'].upper()
        #add similar names (such as VODAFONEGR, vodafone GR, CU) to "VODAFONE"
        if "VODAFONE" in key or "CU" in key:
            opers['VODAFONE GR'] += x['num']
        #similarly for COSMOTE
        elif 'COSMOT' in key or 'COMSOTE' in key:
            opers['COSMOTE GR'] += x['num']
        #add others normally
        else:
            opers[key] = x['num']
    #sort by count of users
    srtdata = sorted(opers, reverse=True, key=opers.get)
    print srtdata
    operssrt = [(x, opers[x]) for x in srtdata]
    return render(request, "webapp/stats.html", {"batterychart": lowperhour, "operators": operssrt})