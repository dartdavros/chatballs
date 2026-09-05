from django.db import migrations


def assign_products_to_sales(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    ProductDepartment = apps.get_model("products", "ProductDepartment")
    Department = apps.get_model("identity", "Department")
    for product in Product.objects.all():
        sales = Department.objects.filter(organization_id=product.organization_id, code="sales").first()
        if sales is not None:
            ProductDepartment.objects.get_or_create(product_id=product.id, department_id=sales.id)


class Migration(migrations.Migration):
    dependencies = [("products", "0002_product_sales_description_product_summary_and_more")]

    operations = [migrations.RunPython(assign_products_to_sales, migrations.RunPython.noop)]
