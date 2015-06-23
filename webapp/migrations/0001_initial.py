# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BaseStation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rid', models.IntegerField(default=-1)),
                ('email', models.CharField(max_length=100)),
                ('operator', models.CharField(max_length=100)),
                ('mcc', models.IntegerField(default=-1)),
                ('mnc', models.IntegerField(default=-1)),
                ('cid', models.IntegerField(default=-1)),
                ('lac', models.IntegerField(default=-1)),
                ('latitude', models.FloatField(default=-1.0)),
                ('longitude', models.FloatField(default=-1.0)),
                ('timestamp', models.DateTimeField()),
            ],
        ),
    ]
