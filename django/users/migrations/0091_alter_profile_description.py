# Generated by Django 5.1.3 on 2024-12-03 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0090_alter_profile_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='description',
            field=models.CharField(default='Ahri: The Nine-Tailed Fox, a mage with charm and spirit fire abilities.'),
        ),
    ]
