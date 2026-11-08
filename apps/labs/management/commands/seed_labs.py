import json
import sqlite3

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.labs.models import CaseStudy, Lab
from apps.labs.seed_data import CASE_STUDIES, PYTHON_QUESTIONS, PYSPARK_QUESTIONS, SQL_QUESTIONS


SQL_TABLES = [
    ("departments", ["id INTEGER", "name TEXT"], [[1, "Engineering"], [2, "Sales"], [3, "Data"]]),
    ("employees", ["id INTEGER", "name TEXT", "department_id INTEGER", "salary INTEGER", "manager_id INTEGER", "hire_date TEXT"], [
        [1, "Anika", 1, 130000, None, "2021-01-03"], [2, "Bilal", 1, 100000, 1, "2022-04-10"],
        [3, "Chen", 1, 100000, 1, "2023-02-14"], [4, "Divya", 2, 90000, 1, "2020-07-08"],
        [5, "Emil", 2, 80000, 4, "2022-08-15"], [6, "Fatima", 3, 70000, 1, "2024-01-11"],
    ]),
    ("customers", ["customer_id TEXT", "name TEXT", "signup_date TEXT"], [
        ["c1", "Mina Shah", "2024-12-10"], ["c2", "Noah Kim", "2025-01-02"],
        ["c3", "Ira Das", "2025-01-05"], ["c4", "Omar Ali", "2025-02-01"],
        ["c5", "Lena Wu", "2025-02-12"],
    ]),
    ("orders", ["order_id INTEGER", "customer_id TEXT", "order_date TEXT", "amount REAL", "status TEXT"], [
        [1, "c1", "2025-01-01", 120.0, "completed"], [2, "c1", "2025-01-03", 40.0, "completed"],
        [3, "c2", "2025-01-03", 75.0, "completed"], [4, "c2", "2025-01-06", 25.0, "cancelled"],
        [5, "c3", "2025-01-04", 200.0, "completed"], [6, "c3", "2025-02-02", 50.0, "pending"],
        [7, "c4", "2025-02-03", 90.0, "completed"], [8, "c4", "2025-02-05", None, "pending"],
        [9, "c1", "2025-02-06", 60.0, "completed"], [10, "c5", "2025-02-08", 30.0, "cancelled"],
    ]),
    ("events", ["event_id INTEGER", "customer_id TEXT", "event_type TEXT", "event_time TEXT"], [
        [101, "c1", "view", "2025-01-01T10:00:00"], [102, "c1", "buy", "2025-01-02T11:00:00"],
        [103, "c2", "view", "2025-01-02T09:00:00"], [104, "c2", "click", "2025-01-03T09:00:00"],
        [105, "c3", "view", "2025-01-03T10:00:00"], [106, "c3", "buy", "2025-01-04T10:00:00"],
        [107, "c4", "click", "2025-02-01T08:00:00"], [108, "c5", "view", "2025-02-02T08:00:00"],
    ]),
    ("logins", ["user_id TEXT", "login_date TEXT"], [
        ["u1", "2025-01-01"], ["u1", "2025-01-02"], ["u1", "2025-01-04"],
        ["u2", "2025-01-02"], ["u2", "2025-01-03"], ["u3", "2025-01-05"],
    ]),
    ("sales", ["sale_date TEXT", "product_id TEXT", "revenue REAL"], [
        ["2025-01-01", "p1", 100.0], ["2025-01-02", "p1", 150.0],
        ["2025-01-04", "p2", 200.0], ["2025-01-06", "p2", 50.0],
        ["2025-02-01", "p1", 300.0],
    ]),
    ("staging_customers", ["source_row_id INTEGER", "customer_id TEXT", "name TEXT", "email TEXT", "updated_at TEXT"], [
        [1, "c1", "Mina", "old@example.com", "2025-01-01T00:00:00"],
        [2, "c1", "Mina Shah", "mina@example.com", "2025-01-03T00:00:00"],
        [3, "c2", "Noah", "noah@example.com", "2025-01-02T00:00:00"],
        [4, "c3", "Ira", "ira@example.com", "2025-01-04T00:00:00"],
    ]),
    ("raw_customers", ["customer_id TEXT", "name TEXT"], [["c1", " Mina "], ["c2", "NOAH"], ["c3", " Ira  Das "]]),
    ("dim_customer", ["customer_id TEXT", "city TEXT", "valid_from TEXT", "valid_to TEXT", "is_current INTEGER"], [
        ["c1", "Pune", "2024-01-01", None, 1], ["c2", "Delhi", "2024-03-01", None, 1],
    ]),
    ("incoming_customer", ["customer_id TEXT", "city TEXT"], [["c1", "Mumbai"], ["c2", "Delhi"], ["c3", "Bengaluru"]]),
    ("web_events", ["event_id INTEGER"], [[1], [2], [3]]),
    ("mobile_events", ["event_id INTEGER"], [[2], [3], [4]]),
]


def _dataset_json():
    return {
        "dialect": "SQLite (browser execution). SQL syntax and functions are not universal.",
        "tables": [
            {"name": name, "columns": columns, "rows": rows}
            for name, columns, rows in SQL_TABLES
        ],
    }


def _related_slugs(category, index):
    question_sets = {
        Lab.Category.PYTHON: PYTHON_QUESTIONS,
        Lab.Category.SQL: SQL_QUESTIONS,
        Lab.Category.PYSPARK: PYSPARK_QUESTIONS,
    }
    questions = question_sets[category]
    neighbors = [neighbor for neighbor in (index - 1, index + 1) if 0 <= neighbor < len(questions)]
    return [slugify(questions[neighbor][0]) for neighbor in neighbors]


def _expected_sql(statement):
    is_transaction = statement.lstrip().upper().startswith("BEGIN;")
    connection = sqlite3.connect(":memory:")
    try:
        for name, columns, rows in SQL_TABLES:
            column_sql = ", ".join(columns)
            connection.execute(f"CREATE TABLE {name} ({column_sql})")
            names = [column.split()[0] for column in columns]
            placeholders = ",".join("?" for _ in names)
            connection.executemany(
                f"INSERT INTO {name} ({', '.join(names)}) VALUES ({placeholders})",
                rows,
            )
        if is_transaction:
            connection.executescript(statement)
            cursor = connection.execute(
                "SELECT customer_id, city, valid_from, valid_to, is_current "
                "FROM dim_customer ORDER BY customer_id, valid_from"
            )
        else:
            cursor = connection.execute(statement)
        if not cursor.description:
            return "Statement executed successfully."
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return json.dumps(rows, default=str, ensure_ascii=False)
    except sqlite3.Error as exc:
        raise ValueError(str(exc)) from exc
    finally:
        connection.close()


def _question_defaults(category, spec, index):
    difficulty = (
        Lab.Difficulty.BEGINNER if index < 12
        else Lab.Difficulty.INTERMEDIATE if index < 27
        else Lab.Difficulty.ADVANCED
    )
    if category == Lab.Category.PYTHON:
        title, subcategory, prompt, starter, solution, expected, sample = spec
        summary = prompt
        sample_input = {"source_example": starter}
        dataset = {"format": "Python values", "source_example": starter}
        tests = [{"name": "Public example", "input": starter, "expected_output": expected}]
        return {
            "category": category, "subcategory": subcategory, "difficulty": difficulty,
            "summary": summary, "instructions": prompt,
            "starter_content": starter, "expected_output": expected,
            "concepts": [subcategory, "Data Engineering", "Correctness"],
            "dataset_definition": dataset, "sample_input": sample_input,
            "constraints": "Preserve the documented output shape. Handle missing or malformed source values explicitly when relevant.",
            "public_test_cases": tests, "hidden_test_cases": [],
            "reference_solution": solution,
            "time_complexity": "Usually O(n) in the number of input records; state the effect of sorting or lookup structures.",
            "space_complexity": "O(k) for the output and any retained lookup state; use streaming when input size is unbounded.",
            "brute_force_explanation": "A direct per-record implementation is easy to reason about. For large inputs, avoid repeated scans and keep only the state required by the transformation.",
            "follow_up_questions": ["How would this behave with a batch larger than memory?", "How would you make retries safe?"],
            "related_questions": _related_slugs(category, index), "execution_mode": "python",
            "required_keywords": [], "evaluation_type": Lab.Evaluation.REVIEW,
            "hints": "Start with the smallest valid record.\nConsider nulls, duplicate keys, and deterministic ordering.",
        }
    if category == Lab.Category.SQL:
        title, subcategory, prompt, solution = spec
        try:
            expected = _expected_sql(solution)
        except ValueError as exc:
            raise ValueError(f"{title}: {exc}") from exc
        tests = [{"name": "Public sample database", "expected_rows": expected}]
        return {
            "category": category, "subcategory": subcategory, "difficulty": difficulty,
            "summary": prompt, "instructions": prompt,
            "starter_content": "-- SQLite exercise. See the schema explorer for sample tables.\n",
            "expected_output": expected, "concepts": [subcategory, "SQL", "Data Engineering"],
            "dataset_definition": _dataset_json(), "sample_input": _dataset_json(),
            "constraints": "Use the supplied sample schema and return the requested columns. Tie-breaking must be deterministic where applicable.",
            "public_test_cases": tests, "hidden_test_cases": [],
            "reference_solution": solution,
            "time_complexity": "Depends on the query plan, indexes, input cardinality, and sort/group operations.",
            "space_complexity": "Depends on intermediate joins, grouping, and window/sort buffers.",
            "brute_force_explanation": "A correlated subquery or repeated scan may be clear for small samples. Compare the plan and use appropriate join keys/indexes for production-scale data.",
            "follow_up_questions": ["Which columns should be indexed and why?", "How do NULL and duplicate rows affect the result?"],
            "related_questions": _related_slugs(category, index), "execution_mode": "sql",
            "required_keywords": [], "evaluation_type": Lab.Evaluation.REVIEW,
            "hints": "Inspect the schema first.\nSQLite-specific: this lab runs SQLite in the browser; date functions, LIMIT, and type behavior differ across SQL dialects.",
        }
    title, subcategory, prompt, starter, solution, sample, expected = spec
    difficulty = (
        Lab.Difficulty.BEGINNER if index < 12
        else Lab.Difficulty.INTERMEDIATE if index < 28
        else Lab.Difficulty.ADVANCED
    )
    spark_rows = {
        "orders": [
            {"order_id": 1, "customer_id": "c1", "amount": 120.0, "status": "completed", "order_date": "2025-01-01"},
            {"order_id": 2, "customer_id": "c1", "amount": 40.0, "status": "completed", "order_date": "2025-01-03"},
            {"order_id": 3, "customer_id": "c2", "amount": 75.0, "status": "pending", "order_date": "2025-01-03"},
        ],
        "customers": [
            {"customer_id": "c1", "segment": "retail", "country": "IN"},
            {"customer_id": "c2", "segment": "business", "country": None},
        ],
        "events": [
            {"event_id": "e1", "customer_id": "c1", "event_time": "2025-01-01T10:00:00", "event_type": "view", "ingest_id": 1},
            {"event_id": "e2", "customer_id": "c1", "event_time": "2025-01-02T10:00:00", "event_type": "buy", "ingest_id": 2},
        ],
        "nested": [
            {"order_id": 1, "customer": {"id": "c1", "address": {"city": "Pune"}}, "items": [{"sku": "p1"}, {"sku": "p2"}]},
        ],
        "architecture": [],
        "streaming": [],
    }
    tables = {"orders": spark_rows["orders"], "customers": spark_rows["customers"], "events": spark_rows["events"], "nested": spark_rows["nested"]}
    active_table = "customers" if subcategory == "Null handling" else "events" if subcategory in {"Deduplication", "Window functions"} and "event" in title.lower() else "orders"
    if subcategory == "Nested JSON":
        active_table = "nested"
    sample_data = {
        "active_table": active_table,
        "tables": tables,
        "schema": list(tables[active_table][0]) if tables[active_table] else [],
    }
    tests = [{"name": "Sample DataFrame", "expected_output": expected}]
    mode = "simulator" if starter and sample != "architecture" and sample != "streaming" else "reading"
    return {
        "category": Lab.Category.PYSPARK, "subcategory": subcategory,
        "difficulty": difficulty, "summary": prompt, "instructions": prompt,
        "starter_content": starter, "expected_output": expected,
        "concepts": [subcategory, "PySpark DataFrame API", "Distributed processing"],
        "dataset_definition": sample_data, "sample_input": sample_data,
        "constraints": "Use actual PySpark APIs in your solution. The browser simulator supports only a documented subset and is not Apache Spark.",
        "public_test_cases": tests, "hidden_test_cases": [],
        "reference_solution": solution,
        "time_complexity": "Cluster-dependent; consider input size, partition count, and shuffle stages.",
        "space_complexity": "Cluster-dependent; account for per-task state, shuffle data, and cached partitions.",
        "brute_force_explanation": "A direct DataFrame transformation is the baseline. For large data, inspect the physical plan, avoid unnecessary shuffles, and validate skew and partition sizing.",
        "follow_up_questions": ["Which operations cause a shuffle?", "How would you validate this on a real Spark cluster?"],
        "related_questions": _related_slugs(category, index), "execution_mode": mode,
        "required_keywords": [], "evaluation_type": Lab.Evaluation.REVIEW,
        "hints": "Read the schema and sample records first.\nThe learning simulator supports only a subset of DataFrame operations; unsupported APIs are reported as unsupported.",
    }


class Command(BaseCommand):
    help = "Seed the Data Engineering Python, SQL, PySpark labs and case studies."

    def handle(self, *args, **options):
        created = 0
        for category, questions in (
            (Lab.Category.PYTHON, PYTHON_QUESTIONS),
            (Lab.Category.SQL, SQL_QUESTIONS),
            (Lab.Category.PYSPARK, PYSPARK_QUESTIONS),
        ):
            for index, spec in enumerate(questions):
                title = spec[0]
                try:
                    defaults = _question_defaults(category, spec, index)
                except ValueError as exc:
                    raise CommandError(f"Unable to prepare question {title!r}: {exc}") from exc
                defaults.update({
                    "title": title,
                    "slug": slugify(title),
                    "display_order": index + 1,
                    "estimated_minutes": 20 if index < 12 else 30,
                    "is_published": True,
                })
                _question, was_created = Lab.objects.get_or_create(
                    slug=defaults["slug"], defaults=defaults
                )
                created += int(was_created)

        Lab.objects.filter(
            slug="select-a-deterministic-latest-record",
            category=Lab.Category.SQL,
        ).update(is_published=False)

        for index, spec in enumerate(CASE_STUDIES):
            title, track, summary, requirements_track, tasks, checkpoints, dataset = spec
            requirements = (
                f"Track: {requirements_track}\n{summary}\n"
                "Design the pipeline so failures are observable, retries are safe, "
                "and data loss or duplication can be detected."
            )
            CaseStudy.objects.get_or_create(
                slug=slugify(title),
                defaults={
                    "title": title, "summary": summary, "track": track,
                    "difficulty": CaseStudy.Difficulty.INTERMEDIATE,
                    "requirements": requirements, "dataset_definition": dataset,
                    "tasks": tasks, "checkpoints": checkpoints,
                    "expected_outcomes": "\n".join(f"- {item}" for item in checkpoints),
                    "display_order": index + 1, "is_published": True,
                },
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(PYTHON_QUESTIONS)} Python, {len(SQL_QUESTIONS)} SQL, "
                f"{len(PYSPARK_QUESTIONS)} PySpark questions and {len(CASE_STUDIES)} case studies "
                f"({created} created; existing content left unchanged)."
            )
        )
