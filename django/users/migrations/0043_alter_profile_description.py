# Generated by Django 5.1.3 on 2024-11-19 16:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0042_alter_profile_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='description',
            field=models.CharField(default='Teemo: The Swift Scout, a yordle with poisonous darts and stealth.'),
        ),
    ]
