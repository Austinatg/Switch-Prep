from django.db import migrations


def correct_seeded_python_examples(apps, schema_editor):
    Lab = apps.get_model("labs", "Lab")
    for lab in Lab.objects.filter(category="python", dataset_definition__format="Python values"):
        sample_input = {"source_example": lab.starter_content}
        dataset_definition = {
            "format": "Python values",
            "source_example": lab.starter_content,
        }
        tests = lab.public_test_cases or []
        if tests and isinstance(tests[0], dict) and tests[0].get("name") == "Public example":
            tests[0]["input"] = lab.starter_content
        lab.sample_input = sample_input
        lab.dataset_definition = dataset_definition
        lab.public_test_cases = tests
        lab.save(update_fields=["sample_input", "dataset_definition", "public_test_cases"])


class Migration(migrations.Migration):
    dependencies = [
        ("labs", "0003_labachievement_and_more"),
    ]

    operations = [
        migrations.RunPython(correct_seeded_python_examples, migrations.RunPython.noop),
    ]
