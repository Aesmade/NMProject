from django.db import models


def toint(x):
    try:
        return int(x)
    except ValueError:
        return -1


def tofloat(x):
    try:
        return float(x)
    except ValueError:
        return -1.0


class BaseStation(models.Model):
    rid = models.IntegerField(default=-1)
    email = models.CharField(max_length=100)
    operator = models.CharField(max_length=100)
    mcc = models.IntegerField(default=-1)
    mnc = models.IntegerField(default=-1)
    cid = models.IntegerField(default=-1)
    lac = models.IntegerField(default=-1)
    latitude = models.FloatField(default=-1.0)
    longitude = models.FloatField(default=-1.0)
    timestamp = models.DateTimeField()

    def __str__(self):
        return str(self.rid) + " " + self.email

    def setdata(self, data):
        self.rid = toint(data[0])
        self.email = data[1]
        self.operator = data[2]
        self.mcc = toint(data[3])
        self.mnc = toint(data[4])
        self.cid = toint(data[5])
        self.lac = toint(data[6])
        self.latitude = tofloat(data[7])
        self.longitude = tofloat(data[8])
        self.timestamp = data[9] + "+03:00"


class BatteryStatus(models.Model):
    rid = models.IntegerField(default=-1)
    email = models.CharField(max_length=100)
    level = models.IntegerField(default=-1)
    plugged = models.IntegerField(default=-1)
    temperature = models.IntegerField(default=-1)
    voltage = models.IntegerField(default=-1)
    timestamp = models.DateTimeField()

    def __str__(self):
        return str(self.rid) + " " + self.email

    def setdata(self, data):
        self.rid = toint(data[0])
        self.email = data[1]
        self.level = toint(data[2])
        self.plugged = toint(data[3])
        self.temperature = toint(data[4])
        self.voltage = toint(data[5])
        self.timestamp = data[6] + "+03:00"


class GPSStatus(models.Model):
    rid = models.IntegerField(default=-1)
    email = models.CharField(max_length=100)
    latitude = models.FloatField(default=-1.0)
    longitude = models.FloatField(default=-1.0)
    timestamp = models.DateTimeField()

    def __str__(self):
        return str(self.rid) + " " + self.email

    def setdata(self, data):
        self.rid = toint(data[0])
        self.email = data[1]
        self.latitude = tofloat(data[2])
        self.longitude = tofloat(data[3])
        self.timestamp = data[4] + "+03:00"


class WifiPos(models.Model):
    ssid = models.CharField(max_length=100)
    bssid = models.CharField(max_length=100)
    latitude = models.FloatField(default=-1.0)
    longitude = models.FloatField(default=-1.0)

    def __str__(self):
        return self.ssid + " - " + self.bssid


class WifiStatus(models.Model):
    rid = models.IntegerField(default=-1)
    email = models.CharField(max_length=100)
    ssid = models.CharField(max_length=100)
    bssid = models.CharField(max_length=100)
    level = models.IntegerField(default=-1)
    frequency = models.IntegerField(default=-1)
    latitude = models.FloatField(default=-1.0)
    longitude = models.FloatField(default=-1.0)
    timestamp = models.DateTimeField()
    realpos = models.ForeignKey(WifiPos, null=True, blank=True)

    def __str__(self):
        return str(self.rid) + " " + self.email

    def setdata(self, data):
        self.rid = toint(data[0])
        self.email = data[1]
        self.ssid = data[2]
        self.bssid = data[3]
        self.level = toint(data[4])
        self.frequency = toint(data[5])
        self.latitude = tofloat(data[6])
        self.longitude = tofloat(data[7])
        self.timestamp = data[8] + "+03:00"