# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0002_batterystatus_gpsstatus_wifistatus'),
    ]

    operations = [
        migrations.CreateModel(
            name='WifiPos',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ssid', models.CharField(max_length=100)),
                ('bssid', models.CharField(max_length=100)),
                ('latitude', models.FloatField(default=-1.0)),
                ('longitude', models.FloatField(default=-1.0)),
            ],
        ),
    ]
