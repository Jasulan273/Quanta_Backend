# Generated by Django 5.1.2 on 2025-01-26 10:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_rename_user_author_author'),
    ]

    operations = [
        migrations.RenameField(
            model_name='author',
            old_name='author',
            new_name='user',
        ),
    ]
