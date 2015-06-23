# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0003_wifipos'),
    ]

    operations = [
        migrations.AddField(
            model_name='wifistatus',
            name='realpos',
            field=models.ForeignKey(default=None, to='webapp.WifiPos'),
        ),
    ]
