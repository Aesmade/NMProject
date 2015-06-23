# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0006_auto_20150620_1331'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wifistatus',
            name='realpos',
            field=models.ForeignKey(blank=True, to='webapp.WifiPos', null=True),
        ),
    ]
