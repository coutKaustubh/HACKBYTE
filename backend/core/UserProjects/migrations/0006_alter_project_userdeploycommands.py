# Generated manually for userDeployCommands TextField + default

from django.db import migrations, models


DEFAULT_CMD = "npm install && npm run build > logs/build.log 2>&1 && npm start"


class Migration(migrations.Migration):

    dependencies = [
        ("UserProjects", "0005_project_userdeploycommands"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="userDeployCommands",
            field=models.TextField(blank=True, default=DEFAULT_CMD),
        ),
    ]
