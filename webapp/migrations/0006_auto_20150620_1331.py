# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0005_auto_20150620_1305'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wifistatus',
            name='realpos',
            field=models.ForeignKey(default=None, blank=True, to='webapp.WifiPos'),
        ),
    ]
