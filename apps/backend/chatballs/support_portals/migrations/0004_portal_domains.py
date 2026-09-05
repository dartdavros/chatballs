from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


def fill_hosted_domains(apps, schema_editor):
    SupportPortal = apps.get_model("support_portals", "SupportPortal")
    base_domain = settings.CHATBALLS_HELP_BASE_DOMAIN.strip().lower().rstrip(".")
    for portal in SupportPortal.objects.all().only("id", "slug"):
        SupportPortal.objects.filter(id=portal.id).update(
            hosted_domain=f"{portal.slug}.{base_domain}"
        )


class Migration(migrations.Migration):
    dependencies = [("support_portals", "0003_category_description")]

    operations = [
        migrations.AddField(
            model_name="supportportal",
            name="hosted_domain",
            field=models.CharField(blank=True, max_length=253),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="supportportal",
            name="custom_domain",
            field=models.CharField(blank=True, default="", max_length=253),
        ),
        migrations.AddField(
            model_name="supportportal",
            name="custom_domain_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(fill_hosted_domains, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="supportportal",
            name="hosted_domain",
            field=models.CharField(max_length=253, unique=True),
        ),
        migrations.AddConstraint(
            model_name="supportportal",
            constraint=models.UniqueConstraint(
                fields=("custom_domain",),
                condition=~Q(custom_domain=""),
                name="uniq_support_portal_custom_domain",
            ),
        ),
    ]
