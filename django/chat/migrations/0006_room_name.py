# Generated by Django 5.1.3 on 2024-11-21 11:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0005_alter_room_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='name',
            field=models.CharField(db_default="'Room '+ id", max_length=200),
        ),
    ]
