# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BatteryStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rid', models.IntegerField(default=-1)),
                ('email', models.CharField(max_length=100)),
                ('level', models.IntegerField(default=-1)),
                ('plugged', models.IntegerField(default=-1)),
                ('temperature', models.IntegerField(default=-1)),
                ('voltage', models.IntegerField(default=-1)),
                ('timestamp', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='GPSStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rid', models.IntegerField(default=-1)),
                ('email', models.CharField(max_length=100)),
                ('latitude', models.FloatField(default=-1.0)),
                ('longitude', models.FloatField(default=-1.0)),
                ('timestamp', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='WifiStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rid', models.IntegerField(default=-1)),
                ('email', models.CharField(max_length=100)),
                ('ssid', models.CharField(max_length=100)),
                ('bssid', models.CharField(max_length=100)),
                ('level', models.IntegerField(default=-1)),
                ('frequency', models.IntegerField(default=-1)),
                ('latitude', models.FloatField(default=-1.0)),
                ('longitude', models.FloatField(default=-1.0)),
                ('timestamp', models.DateTimeField()),
            ],
        ),
    ]
