"""Input-driven reference programs and deterministic cases for Python labs."""

import json
import re
from datetime import datetime


def _dump(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def _program(body):
    return "import json\nimport re\nfrom datetime import datetime\n\ndata = json.loads(input())\n" + body.strip() + "\n"


def _rows(index, *, amount_key="amount"):
    count = index % 6
    result = [
        {"id": f"r{index}-{row}", amount_key: str((row + index) * 1.275)}
        for row in range(count)
    ]
    if index % 4 == 0:
        result.append({"id": f"bad{index}", amount_key: "not-a-number"})
    return result


def _variants(factory, expected):
    cases = []
    for index in range(20):
        data = factory(index)
        cases.append({
            "name": f"Case {index + 1}",
            "stdin": _dump(data),
            "input": data,
            "expected_output": _dump(expected(data)),
        })
    return cases


def _simple_cases(title):
    def factory(index):
        size = index % 7 + 1
        token = f"v{index}"
        if title == "Normalize CSV headers":
            headers = [] if index == 19 else [f"Customer {token}", f"Order-Date {index}", f"  Region/{index}  "]
            return {"headers": headers}
        if title == "Aggregate revenue by customer":
            return {"orders": [{"customer": f"c{n % 3}", "amount": (n + index + 1) * (index + 1)} for n in range(size)]}
        if title == "Count distinct event types":
            return {"events": [f"event-{n % max(1, index % 4)}-{index}" for n in range(size)]}
        if title == "Unpack a source record":
            return {"row": [f"o-{index}", f"c-{index % 5}", round(index * 1.125, 2)]}
        if title == "Standardize whitespace in names":
            return {"names": [] if index == 19 else [f"  Name   {index}  Rao ", f"User\t{index}\nKim"]}
        if title == "Extract email domains":
            values = [f"ops{index}@Example{index % 3}.COM", "invalid", f"data@sub{index}.example.org"]
            if index % 2:
                values.append("bad@@mail")
            return {"emails": values}
        if title == "Build a reusable record normalizer":
            return {"record": {"name": f"  Ana {index}  ", "team": " Data ", "count": index, "active": index % 2 == 0}}
        if title == "Instrument a pipeline function":
            return {"value": f"row-{index}"}
        if title == "Yield rows in bounded batches":
            return {"rows": list(range(index + 1)) if index != 19 else [], "size": index % 5 + 1}
        if title == "Read a CSV without pandas":
            return {"csv": "id,amount\n" + "".join(f"o{n},{n + index}.5\n" for n in range(size))}
        if title == "Flatten nested JSON fields":
            customer = {"id": f"c{index}", "address": {"city": f"City {index}"}} if index % 3 != 2 else {}
            return {"payload": {"event_id": f"event-{index}", "customer": customer}}
        if title == "Retry a transient operation":
            return {"fail_before": index % 5, "attempts": 3 + index % 3, "value": f"ok-{index}"}
        if title == "Fill missing values with pandas":
            return {"rows": [{"record_id": f"r{index}-{n}", "quantity": n if (n + index) % 3 else None, "price": n + 1.5} for n in range(size)]}
        if title == "Clean and parse a date column":
            date = f"2025-{index % 12 + 1:02d}-{index % 27 + 1:02d}"
            return {"rows": [{"name": f"  Name {index}  ", "date": date}, {"name": " Lee ", "date": "invalid"}]}
        if title == "Deduplicate by business key":
            rows = [{"id": f"k{n % 3}", "v": f"old-{index}-{n}"} for n in range(size)]
            rows += [{"id": "k0", "v": f"latest-{index}"}] if index % 2 else []
            return {"rows": rows}
        if title == "Apply a deterministic transformation":
            return {"rows": [{"id": f"r{index}-{n}", "amount": str((n + index) / 7)} for n in range(size)]}
        if title == "Process a large file in chunks":
            return {"text": "".join(f"row-{index}-{n}\n" for n in range(size)), "chunk_size": index % 8 + 1}
        if title == "Assemble a small ETL pipeline":
            return {"rows": [{"id": str(n) if n % 3 != 2 else "", "amount": str((n + 1) * (index + 1))} for n in range(size)]}
        return {}

    def expected(data):
        if title == "Normalize CSV headers":
            return [re.sub(r"[^a-z0-9]+", "_", header.lower()).strip("_") for header in data["headers"]]
        if title == "Aggregate revenue by customer":
            totals = {}
            for order in data["orders"]:
                totals[order["customer"]] = totals.get(order["customer"], 0) + order["amount"]
            return totals
        if title == "Count distinct event types":
            return len(set(data["events"]))
        if title == "Unpack a source record":
            order_id, customer_id, amount = data["row"]
            return {"order_id": order_id, "customer_id": customer_id, "amount": amount}
        if title == "Standardize whitespace in names":
            return [re.sub(r"\s+", " ", name).strip() for name in data["names"]]
        if title == "Extract email domains":
            return [match.group(1).lower() for email in data["emails"] if (match := re.fullmatch(r"[^@\s]+@([^@\s]+)", email))]
        if title == "Build a reusable record normalizer":
            return {key: value.strip() if isinstance(value, str) else value for key, value in data["record"].items()}
        if title == "Instrument a pipeline function":
            value = data["value"]
            return {"calls": ["parse"], "function_name": "parse", "result": value.upper()}
        if title == "Yield rows in bounded batches":
            rows, size = data["rows"], data["size"]
            return [rows[start:start + size] for start in range(0, len(rows), size)]
        if title == "Read a CSV without pandas":
            import csv
            from io import StringIO
            return [{"id": row["id"], "amount": float(row["amount"])} for row in csv.DictReader(StringIO(data["csv"]))]
        if title == "Flatten nested JSON fields":
            customer = data["payload"].get("customer") or {}
            return {"customer_id": customer.get("id"), "city": (customer.get("address") or {}).get("city")}
        if title == "Retry a transient operation":
            calls = min(data["fail_before"], data["attempts"])
            if data["fail_before"] < data["attempts"]:
                calls = data["fail_before"] + 1
                return {"result": data["value"], "calls": calls}
            return {"error": "timeout", "calls": calls}
        if title == "Fill missing values with pandas":
            return [((row["quantity"] or 0) * row["price"]) for row in data["rows"]]
        if title == "Clean and parse a date column":
            output = []
            for row in data["rows"]:
                try:
                    parsed = datetime.fromisoformat(row["date"]).date().isoformat()
                except (TypeError, ValueError):
                    parsed = None
                output.append({"name": row["name"].strip(), "date": parsed})
            return output
        if title == "Deduplicate by business key":
            latest = {row["id"]: row for row in data["rows"]}
            return list(latest.values())
        if title == "Apply a deterministic transformation":
            return [{"id": row["id"], "amount": round(float(row["amount"]), 2)} for row in data["rows"]]
        if title == "Process a large file in chunks":
            text = data["text"]
            size = data["chunk_size"]
            return sum(text[start:start + size].count("\n") for start in range(0, len(text), size))
        if title == "Assemble a small ETL pipeline":
            return [{"id": row["id"], "amount": float(row["amount"])} for row in data["rows"] if row["id"]]
        raise KeyError(title)

    return _variants(factory, expected)


def _advanced_cases(title):
    def factory(index):
        size = index % 6 + 1
        if title == "Filter an incremental batch by watermark":
            watermark = f"2025-01-{index % 20 + 1:02d}T00:00:00"
            rows = [
                {"id": n, "updated": f"2025-01-{min(28, index % 20 + n):02d}T00:00:00"}
                for n in range(size + 1)
            ]
            return {"watermark": watermark, "rows": rows}
        if title == "Merge a Type 1 dimension":
            current = {f"c{n}": {"name": f"Old {index}-{n}", "city": f"City {n}"} for n in range(size)}
            incoming = {f"c{n}": {"name": f"New {index}-{n}"} for n in range(max(0, size - 1), size + 1)}
            return {"current": current, "incoming": incoming}
        if title == "Build Type 2 validity rows":
            return {
                "key": f"c{index % 4}",
                "city": f"City {index}",
                "effective": f"2025-02-{index % 27 + 1:02d}",
                "history": [{"key": f"c{index % 4}", "city": "Old City", "valid_from": "2024-01-01", "valid_to": None, "current": True}],
            }
        if title == "Normalize paginated API payloads":
            items = [{"id": n + index, "value": f"v{n}-{index}"} for n in range(size)]
            return {"response": {"items": items, "next": None if index % 3 == 0 else f"p{index}"}}
        if title == "Parse timestamps safely":
            valid = f"2025-{index % 12 + 1:02d}-{index % 27 + 1:02d}T10:30:00"
            values = [valid, "bad timestamp"] if index % 2 else [valid]
            return {"values": values}
        if title == "Validate required fields":
            record = {"id": index, "name": f"Name {index}"}
            required = ["id", "email"] if index % 2 else ["id", "name"]
            return {"record": record, "required": required}
        if title == "Partition events by date":
            return {"rows": [{"date": f"2025-01-{n % 3 + 1:02d}", "id": n + index} for n in range(size)]}
        if title == "Write a safe newline-delimited file":
            return {"records": [{"id": n + index, "value": f"value {n}"} for n in range(size)]}
        if title == "Convert source types with rejects":
            rows = [{"id": str(n + index)} for n in range(size)]
            if index % 2 == 0:
                rows.append({"id": "bad"})
            return {"rows": rows}
        if title == "Aggregate nested line items":
            return {"order": {"items": [{"price": n + index + 0.5, "quantity": n % 3 + 1} for n in range(size)]}}
        if title == "Sort records deterministically":
            return {"rows": [{"id": n + index, "ts": f"2025-01-{(n % 3) + 1:02d}"} for n in reversed(range(size))]}
        if title == "Join rows using a lookup map":
            customers = [{"id": n, "name": f"Customer {n}"} for n in range(size)]
            orders = [{"customer_id": n % (size + 1), "amount": n + index} for n in range(size + 1)]
            return {"orders": orders, "customers": customers}
        if title == "Compute a rolling total":
            return {"values": [n + index for n in range(size)]}
        if title == "Make a batch load idempotent":
            rows = [{"id": f"k{n % 3}", "v": f"old-{index}-{n}"} for n in range(size)]
            rows.append({"id": "k0", "v": f"last-{index}"})
            return {"rows": rows}
        if title == "Detect schema drift":
            expected = ["id", "amount", "updated"]
            actual = expected[: max(0, 3 - index % 4)] + ([f"extra{index}"] if index % 2 else [])
            record = {key: index for key in actual}
            return {"expected": expected, "record": record}
        if title == "Limit concurrent API requests":
            return {"capacity": index % 5 + 1, "requests": index % 8}
        if title == "Design a recoverable file checkpoint":
            return {"checkpoint": index * 10, "batch_end": index * 10 + 7, "committed": index % 3 != 0}
        return {}

    def expected(data):
        if title == "Filter an incremental batch by watermark":
            return [row for row in data["rows"] if row["updated"] > data["watermark"]]
        if title == "Merge a Type 1 dimension":
            current = {key: dict(value) for key, value in data["current"].items()}
            for key, value in data["incoming"].items():
                current.setdefault(key, {}).update(value)
            return current
        if title == "Build Type 2 validity rows":
            history = [dict(row) for row in data["history"]]
            active = next((row for row in history if row["key"] == data["key"] and row["current"]), None)
            if active and active["city"] != data["city"]:
                active["valid_to"] = data["effective"]
                active["current"] = False
                history.append({"key": data["key"], "city": data["city"], "valid_from": data["effective"], "valid_to": None, "current": True})
            return history
        if title == "Normalize paginated API payloads":
            response = data["response"]
            return {"records": response.get("items", []), "next": response.get("next")}
        if title == "Parse timestamps safely":
            parsed, rejected = [], []
            for value in data["values"]:
                try:
                    parsed.append(datetime.fromisoformat(value).isoformat())
                except (TypeError, ValueError):
                    rejected.append(value)
            return {"parsed": parsed, "rejected": rejected}
        if title == "Validate required fields":
            return [f"Missing required field: {key}" for key in data["required"] if data["record"].get(key) is None or data["record"].get(key) == ""]
        if title == "Partition events by date":
            partitions = {}
            for row in data["rows"]:
                partitions.setdefault(row["date"], []).append(row)
            return partitions
        if title == "Write a safe newline-delimited file":
            return "\n".join(_dump(row) for row in data["records"])
        if title == "Convert source types with rejects":
            valid, rejected = [], []
            for row in data["rows"]:
                try:
                    valid.append({"id": int(row["id"])})
                except (KeyError, TypeError, ValueError):
                    rejected.append(row)
            return {"valid": valid, "rejected": rejected}
        if title == "Aggregate nested line items":
            return sum(item["price"] * item.get("quantity", 1) for item in data["order"].get("items", []))
        if title == "Sort records deterministically":
            return [row["id"] for row in sorted(data["rows"], key=lambda row: (row["ts"], row["id"]))]
        if title == "Join rows using a lookup map":
            names = {customer["id"]: customer["name"] for customer in data["customers"]}
            return [{**order, "customer_name": names.get(order["customer_id"])} for order in data["orders"]]
        if title == "Compute a rolling total":
            return [sum(data["values"][max(0, index - 2):index + 1]) for index in range(len(data["values"]))]
        if title == "Make a batch load idempotent":
            latest = {row["id"]: row for row in data["rows"]}
            return list(latest.values())
        if title == "Detect schema drift":
            actual = set(data["record"])
            expected_keys = set(data["expected"])
            return {"added": sorted(actual - expected_keys), "missing": sorted(expected_keys - actual)}
        if title == "Limit concurrent API requests":
            capacity = data["capacity"]
            requests = data["requests"]
            return {"acquired": min(capacity, requests), "capacity": capacity}
        if title == "Design a recoverable file checkpoint":
            return data["batch_end"] if data["committed"] else data["checkpoint"]
        raise KeyError(title)

    return _variants(factory, expected)


_SIMPLE_PROGRAMS = {
    "Normalize CSV headers": "import re\nheaders = data['headers']\nprint(json.dumps([re.sub(r'[^a-z0-9]+', '_', h.lower()).strip('_') for h in headers], separators=(',', ':')))",
    "Aggregate revenue by customer": "totals = {}\nfor order in data['orders']:\n    totals[order['customer']] = totals.get(order['customer'], 0) + order['amount']\nprint(json.dumps(totals, separators=(',', ':'), sort_keys=True))",
    "Count distinct event types": "print(json.dumps(len(set(data['events']))))",
    "Unpack a source record": "order_id, customer_id, amount = data['row']\nprint(json.dumps({'order_id': order_id, 'customer_id': customer_id, 'amount': amount}, separators=(',', ':')))",
    "Standardize whitespace in names": "print(json.dumps([re.sub(r'\\s+', ' ', name).strip() for name in data['names']], separators=(',', ':')))",
    "Extract email domains": "print(json.dumps([m.group(1).lower() for email in data['emails'] if (m := re.fullmatch(r'[^@\\s]+@([^@\\s]+)', email))], separators=(',', ':')))",
    "Build a reusable record normalizer": "def normalize(record):\n    return {key: value.strip() if isinstance(value, str) else value for key, value in record.items()}\nprint(json.dumps(normalize(data['record']), separators=(',', ':'), sort_keys=True))",
    "Instrument a pipeline function": "from functools import wraps\ncalls = []\ndef counted(fn):\n    @wraps(fn)\n    def wrapper(*args, **kwargs):\n        calls.append(fn.__name__)\n        return fn(*args, **kwargs)\n    return wrapper\n@counted\ndef parse(value):\n    return value.upper()\nresult = parse(data['value'])\nprint(json.dumps({'calls': calls, 'function_name': parse.__name__, 'result': result}, separators=(',', ':')))",
    "Yield rows in bounded batches": "def batches(rows, size):\n    batch = []\n    for row in rows:\n        batch.append(row)\n        if len(batch) == size:\n            yield batch\n            batch = []\n    if batch:\n        yield batch\nprint(json.dumps(list(batches(data['rows'], data['size'])), separators=(',', ':')))",
    "Read a CSV without pandas": "import csv\nfrom io import StringIO\nrows = [{'id': row['id'], 'amount': float(row['amount'])} for row in csv.DictReader(StringIO(data['csv']))]\nprint(json.dumps(rows, separators=(',', ':')))",
    "Flatten nested JSON fields": "customer = data['payload'].get('customer') or {}\nprint(json.dumps({'customer_id': customer.get('id'), 'city': (customer.get('address') or {}).get('city')}, separators=(',', ':'), sort_keys=True))",
    "Retry a transient operation": "calls = 0\ndef flaky():\n    global calls\n    calls += 1\n    if calls <= data['fail_before']:\n        raise TimeoutError('temporary')\n    return data['value']\ndef retry(fn, attempts):\n    for attempt in range(attempts):\n        try:\n            return {'result': fn(), 'calls': calls}\n        except TimeoutError:\n            if attempt == attempts - 1:\n                return {'error': 'timeout', 'calls': calls}\nprint(json.dumps(retry(flaky, data['attempts']), separators=(',', ':'), sort_keys=True))",
    "Fill missing values with pandas": "import pandas as pd\ndf = pd.DataFrame(data['rows'])\nif 'quantity' not in df: df['quantity'] = pd.Series(dtype='float64')\nif 'price' not in df: df['price'] = pd.Series(dtype='float64')\ndf['quantity'] = df['quantity'].fillna(0)\nprint(json.dumps((df['quantity'] * df['price']).tolist(), separators=(',', ':')))",
    "Clean and parse a date column": "import pandas as pd\ndf = pd.DataFrame(data['rows'])\ndf['name'] = df['name'].str.strip()\ndf['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')\ndf['date'] = df['date'].where(df['date'].notna(), None)\nprint(json.dumps(df.to_dict(orient='records'), separators=(',', ':'), sort_keys=True))",
    "Deduplicate by business key": "latest = {row['id']: row for row in data['rows']}\nprint(json.dumps(list(latest.values()), separators=(',', ':'), sort_keys=True))",
    "Apply a deterministic transformation": "print(json.dumps([{'id': row['id'], 'amount': round(float(row['amount']), 2)} for row in data['rows']], separators=(',', ':'), sort_keys=True))",
    "Process a large file in chunks": "text = data['text']\nsize = data['chunk_size']\ncount = sum(text[start:start + size].count('\\n') for start in range(0, len(text), size))\nprint(json.dumps(count))",
    "Assemble a small ETL pipeline": "def etl(rows):\n    return [{'id': row['id'], 'amount': float(row['amount'])} for row in rows if row.get('id')]\nprint(json.dumps(etl(data['rows']), separators=(',', ':'), sort_keys=True))",
    "Filter an incremental batch by watermark": "print(json.dumps([row for row in data['rows'] if row['updated'] > data['watermark']], separators=(',', ':'), sort_keys=True))",
    "Merge a Type 1 dimension": "current = {key: dict(value) for key, value in data['current'].items()}\nfor key, value in data['incoming'].items():\n    current.setdefault(key, {}).update(value)\nprint(json.dumps(current, separators=(',', ':'), sort_keys=True))",
    "Build Type 2 validity rows": "history = [dict(row) for row in data['history']]\nactive = next((row for row in history if row['key'] == data['key'] and row['current']), None)\nif active and active['city'] != data['city']:\n    active['valid_to'] = data['effective']\n    active['current'] = False\n    history.append({'key': data['key'], 'city': data['city'], 'valid_from': data['effective'], 'valid_to': None, 'current': True})\nprint(json.dumps(history, separators=(',', ':'), sort_keys=True))",
    "Normalize paginated API payloads": "response = data['response']\nprint(json.dumps({'records': response.get('items', []), 'next': response.get('next')}, separators=(',', ':'), sort_keys=True))",
    "Parse timestamps safely": "parsed, rejected = [], []\nfor value in data['values']:\n    try:\n        parsed.append(datetime.fromisoformat(value).isoformat())\n    except (TypeError, ValueError):\n        rejected.append(value)\nprint(json.dumps({'parsed': parsed, 'rejected': rejected}, separators=(',', ':'), sort_keys=True))",
    "Validate required fields": "errors = [f'Missing required field: {key}' for key in data['required'] if data['record'].get(key) is None or data['record'].get(key) == '']\nprint(json.dumps(errors, separators=(',', ':')))",
    "Partition events by date": "parts = {}\nfor row in data['rows']:\n    parts.setdefault(row['date'], []).append(row)\nprint(json.dumps(parts, separators=(',', ':'), sort_keys=True))",
    "Write a safe newline-delimited file": "content = '\\n'.join(json.dumps(row, separators=(',', ':'), sort_keys=True) for row in data['records'])\nprint(json.dumps(content, separators=(',', ':')))",
    "Convert source types with rejects": "valid, rejected = [], []\nfor row in data['rows']:\n    try:\n        valid.append({'id': int(row['id'])})\n    except (KeyError, TypeError, ValueError):\n        rejected.append(row)\nprint(json.dumps({'valid': valid, 'rejected': rejected}, separators=(',', ':'), sort_keys=True))",
    "Aggregate nested line items": "total = sum(item['price'] * item.get('quantity', 1) for item in data['order'].get('items', []))\nprint(json.dumps(total))",
    "Sort records deterministically": "print(json.dumps([row['id'] for row in sorted(data['rows'], key=lambda row: (row['ts'], row['id']))], separators=(',', ':')))",
    "Join rows using a lookup map": "names = {customer['id']: customer['name'] for customer in data['customers']}\nresult = [{**order, 'customer_name': names.get(order['customer_id'])} for order in data['orders']]\nprint(json.dumps(result, separators=(',', ':'), sort_keys=True))",
    "Compute a rolling total": "values = data['values']\nprint(json.dumps([sum(values[max(0, i - 2):i + 1]) for i in range(len(values))], separators=(',', ':')))",
    "Make a batch load idempotent": "latest = {row['id']: row for row in data['rows']}\nprint(json.dumps(list(latest.values()), separators=(',', ':'), sort_keys=True))",
    "Detect schema drift": "actual, expected = set(data['record']), set(data['expected'])\nprint(json.dumps({'added': sorted(actual - expected), 'missing': sorted(expected - actual)}, separators=(',', ':'), sort_keys=True))",
    "Limit concurrent API requests": "from threading import BoundedSemaphore\nlimit = BoundedSemaphore(data['capacity'])\nacquired = 0\nfor _ in range(data['requests']):\n    if limit.acquire(blocking=False): acquired += 1\nprint(json.dumps({'acquired': acquired, 'capacity': data['capacity']}, separators=(',', ':'), sort_keys=True))",
    "Design a recoverable file checkpoint": "checkpoint = data['checkpoint']\nif data['committed']: checkpoint = data['batch_end']\nprint(json.dumps(checkpoint))",
}


def cases_for(title):
    if title == "Filter incomplete records":
        from .seed_data import FILTER_CASES, _filtered_rows

        cases = []
        for name, rows in FILTER_CASES:
            stdin = _dump(rows)
            cases.append({
                "name": name,
                "stdin": stdin,
                "input": rows,
                "expected_output": _dump(_filtered_rows(rows)),
            })
        return cases
    if title in {
        "Filter an incremental batch by watermark",
        "Merge a Type 1 dimension",
        "Build Type 2 validity rows",
        "Normalize paginated API payloads",
        "Parse timestamps safely",
        "Validate required fields",
        "Partition events by date",
        "Write a safe newline-delimited file",
        "Convert source types with rejects",
        "Aggregate nested line items",
        "Sort records deterministically",
        "Join rows using a lookup map",
        "Compute a rolling total",
        "Make a batch load idempotent",
        "Detect schema drift",
        "Limit concurrent API requests",
        "Design a recoverable file checkpoint",
    }:
        return _advanced_cases(title)
    return _simple_cases(title)


def program_for(title):
    if title == "Filter incomplete records":
        from .seed_data import FILTER_STARTER

        return FILTER_STARTER
    return _program(_SIMPLE_PROGRAMS[title])


def starter_for(title):
    if title == "Normalize CSV headers":
        return (
            "def solve(headers):\n"
            "    normalized = []\n"
            "    for header in headers:\n"
            "        # Convert each header to lowercase snake_case.\n"
            "        pass\n"
            "    return normalized\n"
        )
    imports = "import json\n"
    if title in {"Fill missing values with pandas", "Clean and parse a date column"}:
        imports += "import pandas as pd\n"
    return (
        imports
        + "\ndata = json.loads(input())\n"
        + "# TODO: transform the input data for this question and print the result as JSON.\n"
    )
