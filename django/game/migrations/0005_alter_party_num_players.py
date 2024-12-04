# Generated by Django 5.1.2 on 2024-10-12 13:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0004_alter_party_num_players'),
    ]

    operations = [
        migrations.AlterField(
            model_name='party',
            name='num_players',
            field=models.IntegerField(choices=[(1, 'Play with AI'), (2, '2 Players'), (3, '3 Players')], default=1),
        ),
    ]