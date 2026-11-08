(() => {
  const editor = document.getElementById("code-editor");
  if (!editor) return;

  const workspace = document.querySelector(".coding-panel");
  const mode = workspace?.dataset.mode || "reading";
  const pythonFunctionInput = workspace?.dataset.pythonFunctionInput || "";
  const statusEl = document.getElementById("execution-status");
  const outputEl = document.getElementById("execution-output");
  const saveStatus = document.getElementById("save-status");
  let monacoEditor = null;
  let pyodide = null;
  let sqlDb = null;
  let dataset = {};
  try {
    dataset = JSON.parse(document.getElementById("lab-dataset")?.textContent || "{}");
  } catch {
    dataset = {};
  }

  const currentCode = () => monacoEditor ? monacoEditor.getValue() : editor.value;
  const setCode = (value) => {
    editor.value = value;
    if (monacoEditor) monacoEditor.setValue(value);
  };
  const setStatus = (text, state = "") => {
    statusEl.textContent = text;
    statusEl.dataset.state = state;
  };
  const showOutput = (text) => {
    outputEl.textContent = text || "(No output)";
  };
  const clearTestResults = () => {
    const results = document.getElementById("test-results");
    if (!results) return;
    results.replaceChildren();
    results.hidden = true;
  };
  const showPassedTests = (names) => {
    const results = document.getElementById("test-results");
    if (!results) return;
    results.replaceChildren();
    const heading = document.createElement("h3");
    heading.textContent = `All ${names.length} test case${names.length === 1 ? "" : "s"} passed`;
    const list = document.createElement("ul");
    names.forEach((name) => {
      const item = document.createElement("li");
      item.textContent = name;
      list.appendChild(item);
    });
    results.append(heading, list);
    results.hidden = false;
  };
  const readJson = (id, fallback = []) => {
    try {
      return JSON.parse(document.getElementById(id)?.textContent || JSON.stringify(fallback));
    } catch {
      return fallback;
    }
  };
  const parsedPublicTests = readJson("lab-public-test-cases");
  const parsedHiddenTests = readJson("lab-hidden-test-cases");
  const publicTestCases = Array.isArray(parsedPublicTests) ? parsedPublicTests : [];
  const hiddenTestCases = Array.isArray(parsedHiddenTests) ? parsedHiddenTests : [];
  const expectedOutput = () => {
    try {
      return JSON.parse(document.getElementById("lab-expected-output")?.textContent || '""');
    } catch {
      return "";
    }
  };
  const stableJson = (value) => {
    if (Array.isArray(value)) return value.map(stableJson);
    if (value && typeof value === "object") {
      return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableJson(value[key])]));
    }
    return value;
  };
  const outputsMatch = (actual, expected) => {
    try {
      return JSON.stringify(stableJson(JSON.parse(actual))) === JSON.stringify(stableJson(JSON.parse(expected)));
    } catch {
      return actual.trim() === String(expected).trim();
    }
  };
  const cookie = (name) => {
    const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : "";
  };
  const showTable = (container, columns, rows) => {
    if (!columns?.length) {
      container.textContent = "No result rows.";
      return;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "result-table-wrap";
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const header = document.createElement("tr");
    columns.forEach((column) => {
      const th = document.createElement("th");
      th.textContent = column;
      header.appendChild(th);
    });
    head.appendChild(header);
    table.appendChild(head);
    const body = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      row.forEach((value) => {
        const td = document.createElement("td");
        td.textContent = value === null ? "NULL" : String(value);
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    table.appendChild(body);
    wrapper.appendChild(table);
    container.appendChild(wrapper);
  };

  function initializeMonaco(attempt = 0) {
    if (typeof window.require !== "function") {
      if (attempt < 50) window.setTimeout(() => initializeMonaco(attempt + 1), 100);
      return;
    }
    const base = "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs";
    window.require.config({ paths: { vs: base } });
    window.require(["vs/editor/editor.main"], () => {
      const language = mode === "sql" ? "sql" : mode === "simulator" ? "python" : "python";
      monacoEditor = window.monaco.editor.create(document.getElementById("monaco-editor"), {
        value: editor.value,
        language,
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 13,
        tabSize: 4,
        scrollBeyondLastLine: false,
        wordWrap: "on",
        quickSuggestions: true,
      });
      document.getElementById("monaco-editor").style.display = "block";
      editor.hidden = true;
      monacoEditor.onDidChangeModelContent(() => {
        editor.value = monacoEditor.getValue();
      });
    }, () => {
      setStatus("Editor unavailable; using plain text editor.", "warning");
    });
  }

  async function loadPyodide() {
    if (pyodide) return pyodide;
    setStatus("Loading Python runtime…", "loading");
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js";
      script.onload = resolve;
      script.onerror = () => reject(new Error("Could not load Pyodide. Check your internet connection and try again."));
      document.head.appendChild(script);
    });
    pyodide = await window.loadPyodide();
    return pyodide;
  }

  async function executePython(code, inputText) {
    const runtime = await loadPyodide();
    if (code.includes("import pandas")) {
      setStatus("Loading pandas…", "loading");
      await runtime.loadPackage("pandas");
    }
    const stdout = [];
    const stderr = [];
    const inputBytes = Array.from(new TextEncoder().encode(`${inputText}\n`));
    runtime.setStdout({ batched: (line) => stdout.push(line) });
    runtime.setStderr({ batched: (line) => stderr.push(line) });
    runtime.setStdin({ stdin: () => inputBytes.length ? inputBytes.shift() : null });
    const functionRunner = pythonFunctionInput
      ? `\nimport json as __lab_json\n__lab_data = __lab_json.loads(input())\nprint(__lab_json.dumps(solve(__lab_data[${JSON.stringify(pythonFunctionInput)}]), separators=(",", ":")))\n`
      : "";
    const isolatedScript = `exec(compile(${JSON.stringify(code + functionRunner)}, "<lab-submission>", "exec"), {"__name__": "__main__"})`;
    const result = await runtime.runPythonAsync(isolatedScript);
    const pieces = [...stdout];
    if (stderr.length) pieces.push(stderr.join("\n"));
    if (!pieces.length && result !== undefined && result !== null) {
      pieces.push(String(result));
    }
    return pieces.join("\n").trim() || "(Code completed without printed output)";
  }

  async function runPython() {
    try {
      setStatus("Running in browser…", "loading");
      const actual = await executePython(currentCode(), document.getElementById("program-input")?.value || "");
      showOutput(actual);
      const expected = expectedOutput();
      if (expected && actual === String(expected).trim()) {
        setStatus("Matches public sample output · browser-only", "success");
      } else {
        setStatus("Completed in browser · sample result not matched", "warning");
      }
    } catch (error) {
      showOutput(error?.message || String(error));
      setStatus("Execution error", "error");
    }
  }

  async function submitBrowserReport(passedCount, total) {
    const formElement = document.getElementById("lab-submit-form");
    document.getElementById("submit-answer").value = currentCode().trim();
    const form = new FormData(formElement);
    form.append("browser_report", JSON.stringify({
      mode,
      passed_count: passedCount,
      total,
      passed: passedCount === total,
    }));
    const response = await fetch(formElement.action, {
      method: "POST",
      body: form,
      credentials: "same-origin",
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Your result could not be saved.");
    setStatus(result.feedback, result.status === "passed" ? "success" : "warning");
    return result;
  }

  async function gradePython() {
    const button = document.querySelector("#lab-submit-form button[type='submit']");
    button.disabled = true;
    try {
      const tests = [
        ...publicTestCases.map((test) => ({
          ...test,
          stdin: test.stdin ?? document.getElementById("program-input")?.value ?? "",
        })),
        ...hiddenTestCases.map((test) => ({ ...test, stdin: test.stdin ?? test.input ?? "" })),
      ];
      if (!tests.length) throw new Error("This Python question has no configured expected-output test cases.");
      if (tests.some((test) => !test || typeof test.expected_output !== "string")) {
        throw new Error("A configured Python test case is missing its expected output.");
      }

      let passedCount = 0;
      for (let index = 0; index < tests.length; index += 1) {
        const test = tests[index];
        setStatus(`Running test ${index + 1} of ${tests.length} in your browser…`, "loading");
        try {
          const actual = await executePython(currentCode(), String(test.stdin));
          const passed = outputsMatch(actual, test.expected_output);
          if (passed) passedCount += 1;
        } catch {
          // A failed case is intentionally not identified in learner-facing output.
        }
      }
      const result = await submitBrowserReport(passedCount, tests.length);
      if (result.status === "passed") {
        showOutput("Congratulations! Your solution passed every test case.");
        showPassedTests(tests.map((test, index) => test.name || `Test case ${index + 1}`));
      } else {
        showOutput("Some test cases failed. The individual cases are hidden; review your solution and try again.");
        clearTestResults();
      }
    } catch (error) {
      showOutput(error?.message || String(error));
      setStatus("Could not run or save tests.", "error");
    } finally {
      button.disabled = false;
    }
  }

  function validIdentifier(value) {
    return /^[A-Za-z_][A-Za-z0-9_]*$/.test(value);
  }

  async function loadSqlite() {
    if (sqlDb) return sqlDb;
    setStatus("Loading SQLite…", "loading");
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/sql-wasm.js";
      script.onload = resolve;
      script.onerror = () => reject(new Error("Could not load browser SQLite. Check your internet connection and try again."));
      document.head.appendChild(script);
    });
    const SQL = await window.initSqlJs({
      locateFile: (file) => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${file}`,
    });
    sqlDb = new SQL.Database();
    (dataset.tables || []).forEach((table) => {
      if (!validIdentifier(table.name) || !Array.isArray(table.columns)) return;
      const definitions = table.columns.map((column) => {
        const [name, type = "TEXT"] = String(column).trim().split(/\s+/, 2);
        if (!validIdentifier(name) || !/^(INTEGER|REAL|TEXT|NUMERIC|BLOB)$/i.test(type)) {
          throw new Error(`Unsupported schema definition: ${column}`);
        }
        return `"${name}" ${type}`;
      });
      sqlDb.run(`CREATE TABLE "${table.name}" (${definitions.join(", ")})`);
      (table.rows || []).forEach((row) => {
        const columns = table.columns.map((column) => `"${String(column).trim().split(/\s+/, 1)[0]}"`);
        const placeholders = row.map(() => "?").join(", ");
        sqlDb.run(`INSERT INTO "${table.name}" (${columns.join(", ")}) VALUES (${placeholders})`, row);
      });
    });
    renderSchema();
    return sqlDb;
  }

  function renderSchema() {
    const target = document.getElementById("schema-explorer-content");
    if (!target) return;
    target.replaceChildren();
    (dataset.tables || []).forEach((table) => {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = `${table.name} (${(table.rows || []).length} sample rows)`;
      details.appendChild(summary);
      const fields = document.createElement("p");
      fields.textContent = (table.columns || []).join(", ");
      details.appendChild(fields);
      const sample = document.createElement("pre");
      sample.textContent = JSON.stringify((table.rows || []).slice(0, 3), null, 2);
      details.appendChild(sample);
      target.appendChild(details);
    });
  }

  async function runSql() {
    try {
      if (sqlDb) sqlDb.close();
      sqlDb = null;
      const db = await loadSqlite();
      setStatus("Running SQLite query…", "loading");
      const results = db.exec(currentCode());
      if (!results.length) {
        showOutput("Statement completed. No result set was returned.");
        const matched = expectedOutput() === "Statement executed successfully.";
        setStatus(matched ? "Matches expected statement result · browser-only" : "Statement completed · no result set", matched ? "success" : "warning");
        return matched;
      }
      outputEl.replaceChildren();
      results.forEach((result) => {
        const heading = document.createElement("p");
        heading.textContent = `${result.values.length} row(s)`;
        outputEl.appendChild(heading);
        showTable(outputEl, result.columns, result.values);
      });
      const last = results[results.length - 1];
      const actualRows = last.values.map((row) => Object.fromEntries(last.columns.map((column, index) => [column, row[index]])));
      let matches = false;
      try {
        const expected = JSON.parse(expectedOutput());
        matches = JSON.stringify(stableJson(actualRows)) === JSON.stringify(stableJson(expected));
      } catch {
        matches = false;
      }
      setStatus(matches ? "Matches expected SQLite sample · browser-only" : "Result differs from expected SQLite sample", matches ? "success" : "warning");
      return matches;
    } catch (error) {
      showOutput(error?.message || String(error));
      setStatus("SQL error", "error");
      return false;
    }
  }

  function splitArgs(source) {
    const result = [];
    let start = 0;
    let depth = 0;
    let quote = "";
    for (let i = 0; i < source.length; i += 1) {
      const char = source[i];
      if (quote) {
        if (char === quote && source[i - 1] !== "\\") quote = "";
      } else if (char === "'" || char === '"') quote = char;
      else if ("([{".includes(char)) depth += 1;
      else if (")]}".includes(char)) depth -= 1;
      else if (char === "," && depth === 0) {
        result.push(source.slice(start, i).trim());
        start = i + 1;
      }
    }
    if (source.slice(start).trim()) result.push(source.slice(start).trim());
    return result;
  }

  function quotedValues(source) {
    return [...source.matchAll(/['"]([^'"]+)['"]/g)].map((match) => match[1]);
  }

  function getColumn(row, name) {
    return String(name).split(".").reduce((value, key) => value?.[key], row);
  }

  function parseFilter(term, row) {
    const nullCheck = term.match(/(?:F\.)?col\(['"]([^'"]+)['"]\)\.(isNotNull|isNull)\(\)/);
    if (nullCheck) {
      const empty = getColumn(row, nullCheck[1]) == null;
      return nullCheck[2] === "isNull" ? empty : !empty;
    }
    const operatorMatch = term.match(/(==|!=|>=|<=|>|<|=)\s*(.+)$/);
    const column = term.match(/(?:F\.)?col\(['"]([^'"]+)['"]\)/)?.[1]
      || term.match(/^\s*([A-Za-z_]\w*)\s*(?:==|!=|>=|<=|>|<|=)/)?.[1];
    if (!column || !operatorMatch) throw new Error(`Simulator does not support this filter expression: ${term}`);
    const operator = operatorMatch[1];
    let right = operatorMatch[2].trim();
    const literalMatch = right.match(/(?:F\.)?lit\(([^)]+)\)/);
    if (literalMatch) right = literalMatch[1];
    if (right === "True") right = true;
    else if (right === "False") right = false;
    else if (/^['"]/.test(String(right))) right = String(right).slice(1, -1);
    else if (right !== undefined && right !== "" && !Number.isNaN(Number(right))) right = Number(right);
    const left = getColumn(row, column);
    if (left == null) return false;
    if (operator === "==" || operator === "=") return left == right;
    if (operator === "!=") return left != right;
    if (operator === ">") return left > right;
    if (operator === "<") return left < right;
    if (operator === ">=") return left >= right;
    return left <= right;
  }

  function filterRows(rows, expression) {
    const clauses = expression.split(/\s*&\s*/).map((clause) => {
      let normalized = clause.trim().replace(/^\((.*)\)$/s, "$1");
      const wrapped = normalized.match(/^(["'])([\s\S]*)\1$/);
      if (wrapped) normalized = wrapped[2];
      return normalized;
    });
    return rows.filter((row) => clauses.every((clause) => parseFilter(clause, row)));
  }

  function transformColumn(rows, args) {
    if (args.length < 2) throw new Error("withColumn requires a column name and supported expression.");
    const name = args[0].replace(/^['"]|['"]$/g, "");
    const expression = args.slice(1).join(",");
    const result = rows.map((row) => {
      let value;
      const source = expression.match(/(?:F\.)?col\(['"]([^'"]+)['"]\)/);
      const literal = expression.match(/(?:F\.)?lit\(([^)]+)\)/);
      if (/lower\(/i.test(expression) && source) value = String(getColumn(row, source[1]) ?? "").toLowerCase();
      else if (/upper\(/i.test(expression) && source) value = String(getColumn(row, source[1]) ?? "").toUpperCase();
      else if (/trim\(/i.test(expression) && source) value = String(getColumn(row, source[1]) ?? "").trim();
      else if (literal) value = literal[1].replace(/^['"]|['"]$/g, "");
      else if (source) value = row[source[1]];
      else throw new Error(`Simulator does not support this withColumn expression: ${expression}`);
      return { ...row, [name]: value };
    });
    return result;
  }

  function aggregateRows(rows, groupColumns, expression) {
    const groups = new Map();
    rows.forEach((row) => {
      const key = JSON.stringify(groupColumns.map((column) => row[column]));
      if (!groups.has(key)) groups.set(key, { rows: [], values: groupColumns.map((column) => row[column]) });
      groups.get(key).rows.push(row);
    });
    const aggregateCalls = [...expression.matchAll(/(?:F\.)?(count|sum|avg|min|max)\s*\(\s*(?:(?:F\.)?col\(['"]([^'"]+)['"]\)|(['"]?\*)['"]?)\s*\)\.alias\(['"]([^'"]+)['"]\)/gi)];
    if (!aggregateCalls.length) throw new Error("Simulator supports count, sum, avg, min and max with alias().");
    const columns = [...groupColumns, ...aggregateCalls.map((match) => match[4])];
    const output = [...groups.values()].map((group) => {
      const row = Object.fromEntries(groupColumns.map((column, i) => [column, group.values[i]]));
      aggregateCalls.forEach((call) => {
        const op = call[1].toLowerCase();
        const field = call[2] || (call[3] ? "*" : null);
        const alias = call[4];
        const values = field === "*" ? group.rows : group.rows.map((item) => item[field]).filter((item) => item != null);
        if (op === "count") row[alias] = values.length;
        else if (!values.length) row[alias] = null;
        else if (op === "sum") row[alias] = values.reduce((total, value) => total + Number(value), 0);
        else if (op === "avg") row[alias] = values.reduce((total, value) => total + Number(value), 0) / values.length;
        else if (op === "min") row[alias] = values.reduce((a, b) => a < b ? a : b);
        else row[alias] = values.reduce((a, b) => a > b ? a : b);
      });
      return row;
    });
    return { rows: output, columns };
  }

  function simulatePySpark() {
    const source = currentCode();
    const unsupported = [
      [/\bWindow\b/, "window functions"],
      [/writeStream|readStream/, "Structured Streaming"],
      [/\.cache\s*\(|\.persist\s*\(/, "caching and persistence"],
      [/broadcast\s*\(/, "broadcast join execution"],
      [/\.mapPartitions\s*\(|\.rdd\b/, "RDD operations"],
      [/\.parquet\s*\(|\.write\s*\./, "Spark file writes"],
      [/\.collect\s*\(/, "collecting Spark results"],
      [/\.explode\s*\(|\bexplode\s*\(/, "explode"],
    ].find(([pattern]) => pattern.test(source));
    if (unsupported) throw new Error(`${unsupported[1]} are not supported by the browser simulator; run this exercise in Apache Spark.`);
    const active = dataset.active_table || Object.keys(dataset.tables || {})[0];
    let rows = [...(dataset.tables?.[active] || [])];
    let columns = rows.length ? Object.keys(rows[0]) : (dataset.schema || []);
    let note = "Browser-side DataFrame subset; this is not Apache Spark.";
    const operations = [...source.matchAll(/\.(select|filter|where|withColumn|groupBy|join|dropDuplicates|drop|distinct|limit|orderBy|repartition|coalesce|printSchema|show)\s*\(|(?<!F)\.count\s*\(/g)];
    if (!operations.length) throw new Error("No supported DataFrame operation found. Try select, filter, withColumn, groupBy, or join.");
    for (let i = 0; i < operations.length; i += 1) {
      const match = operations[i];
      const op = match[1] || "count";
      const open = source.indexOf("(", match.index);
      let depth = 1;
      let end = open + 1;
      let quote = "";
      for (; end < source.length && depth; end += 1) {
        const ch = source[end];
        if (quote) {
          if (ch === quote && source[end - 1] !== "\\") quote = "";
        } else if (ch === "'" || ch === '"') quote = ch;
        else if (ch === "(") depth += 1;
        else if (ch === ")") depth -= 1;
      }
      const argument = source.slice(open + 1, end - 1);
      const args = splitArgs(argument);
      if (op === "printSchema" || op === "show") {
        continue;
      } else if (op === "select") {
        if (/explode|alias|struct|when|to_date/i.test(argument)) throw new Error("Simulator does not support this complex select expression.");
        const names = quotedValues(argument);
        if (!names.length) throw new Error("Simulator select needs named columns.");
        rows = rows.map((row) => Object.fromEntries(names.map((name) => [name, row[name]])));
        columns = names;
      } else if (op === "filter" || op === "where") {
        rows = filterRows(rows, argument);
      } else if (op === "withColumn") {
        rows = transformColumn(rows, args);
        columns = rows.length ? Object.keys(rows[0]) : [...columns, args[0]?.replace(/^['"]|['"]$/g, "")];
      } else if (op === "groupBy") {
        const groups = quotedValues(argument);
        const aggregateStart = source.slice(end).search(/\.agg\s*\(/);
        if (aggregateStart < 0) throw new Error("groupBy must be followed by a supported agg() call.");
        const absoluteStart = end + aggregateStart;
        const aggOpen = source.indexOf("(", absoluteStart);
        let aggDepth = 1;
        let aggEnd = aggOpen + 1;
        let aggQuote = "";
        for (; aggEnd < source.length && aggDepth; aggEnd += 1) {
          const ch = source[aggEnd];
          if (aggQuote) {
            if (ch === aggQuote && source[aggEnd - 1] !== "\\") aggQuote = "";
          } else if (ch === "'" || ch === '"') aggQuote = ch;
          else if (ch === "(") aggDepth += 1;
          else if (ch === ")") aggDepth -= 1;
        }
        const aggregate = aggregateRows(rows, groups, source.slice(aggOpen + 1, aggEnd - 1));
        rows = aggregate.rows;
        columns = aggregate.columns;
      } else if (op === "join") {
        const other = Object.keys(dataset.tables || {}).find((name) => name !== active && source.slice(match.index, end).includes(name));
        if (!other) throw new Error("Simulator join needs a named sample table in the dataset.");
        const key = quotedValues(argument)[0];
        const joinType = quotedValues(argument)[1] || "inner";
        if (!key) throw new Error("Simulator join requires a single named join key.");
        if (!["inner", "left"].includes(joinType)) throw new Error(`Simulator does not support ${joinType} joins.`);
        const right = dataset.tables[other];
        const joined = [];
        rows.forEach((left) => {
          const matches = right.filter((item) => item[key] === left[key]);
          if (matches.length) matches.forEach((item) => joined.push({ ...item, ...left }));
          else if (joinType === "left") joined.push({ ...left });
        });
        rows = joined;
        columns = rows.length ? Object.keys(rows[0]) : columns;
      } else if (op === "dropDuplicates" || op === "distinct") {
        const keys = op === "distinct" ? columns : quotedValues(argument);
        const seen = new Set();
        rows = rows.filter((row) => {
          const key = JSON.stringify(keys.length ? keys.map((name) => row[name]) : row);
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
      } else if (op === "drop") {
        const names = quotedValues(argument);
        rows = rows.map((row) => Object.fromEntries(Object.entries(row).filter(([key]) => !names.includes(key))));
        columns = columns.filter((name) => !names.includes(name));
      } else if (op === "limit") {
        rows = rows.slice(0, Number(args[0]));
      } else if (op === "count") {
        rows = [{ count: rows.length }];
        columns = ["count"];
      } else if (op === "orderBy") {
        const names = quotedValues(argument);
        if (names.length) {
          const direction = /\.desc\s*\(/.test(argument) ? -1 : 1;
          rows = [...rows].sort((a, b) => {
            const left = getColumn(a, names[0]);
            const right = getColumn(b, names[0]);
            const compared = typeof left === "number" && typeof right === "number"
              ? left - right
              : String(left).localeCompare(String(right));
            return compared * direction;
          });
        }
      } else {
        note += ` Operation ${op} was treated as metadata only; partition and cluster behavior is not simulated.`;
      }
    }
    showOutput(`${note}\n${JSON.stringify({ schema: columns, rows }, null, 2)}`);
    setStatus("Simulated DataFrame output · not Spark execution", "warning");
  }

  document.getElementById("run-code")?.addEventListener("click", () => {
    if (mode === "python") runPython();
    else if (mode === "sql") runSql();
    else if (mode === "simulator") {
      try {
        simulatePySpark();
      } catch (error) {
        showOutput(error?.message || String(error));
        setStatus("Unsupported operation or simulator error", "warning");
      }
    }
  });

  document.getElementById("reset-code")?.addEventListener("click", () => {
    setCode(document.getElementById("starter-template").value);
    setStatus("Starter restored");
  });
  document.getElementById("copy-code")?.addEventListener("click", async (event) => {
    try {
      await navigator.clipboard.writeText(currentCode());
      event.currentTarget.textContent = "Copied";
      window.setTimeout(() => { event.currentTarget.textContent = "Copy"; }, 1200);
    } catch {
      setStatus("Copy is unavailable in this browser.", "warning");
    }
  });

  document.getElementById("save-draft")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    saveStatus.textContent = "Saving…";
    try {
      const form = new FormData();
      form.append("content", currentCode());
      const response = await fetch(button.dataset.url, {
        method: "POST",
        headers: { "X-CSRFToken": cookie("csrftoken") },
        body: form,
        credentials: "same-origin",
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Draft could not be saved.");
      saveStatus.textContent = "Draft saved to your account.";
    } catch (error) {
      saveStatus.textContent = error.message || "Draft could not be saved.";
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("bookmark-button")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const response = await fetch(button.dataset.url, {
        method: "POST",
        headers: { "X-CSRFToken": cookie("csrftoken") },
        credentials: "same-origin",
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Bookmark could not be updated.");
      button.setAttribute("aria-pressed", String(result.bookmarked));
      button.textContent = result.bookmarked ? "★ Bookmarked" : "☆ Bookmark";
    } catch (error) {
      window.alert(error.message || "Bookmark could not be updated.");
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("lab-submit-form")?.addEventListener("submit", async (event) => {
    if (mode === "python" || mode === "sql") {
      event.preventDefault();
      if (!currentCode().trim()) {
        setStatus("Add a solution before running tests.", "warning");
        return;
      }
      const button = event.currentTarget.querySelector("button[type='submit']");
      button.disabled = true;
      try {
        if (mode === "python") {
          clearTestResults();
          await gradePython();
        } else {
          clearTestResults();
          const matched = await runSql();
          const result = await submitBrowserReport(matched ? 1 : 0, 1);
          if (result.status === "passed") {
            showPassedTests(["Expected result matched"]);
          } else {
            clearTestResults();
          }
        }
      } catch (error) {
        showOutput(error?.message || String(error));
        setStatus("Could not run or save tests.", "error");
      } finally {
        button.disabled = false;
      }
      return;
    }
    const answer = document.getElementById("submit-answer");
    answer.value = currentCode().trim();
    if (!answer.value) {
      event.preventDefault();
      setStatus("Add a solution before submitting.", "warning");
    }
  });

  document.querySelectorAll("[data-ai-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const root = document.querySelector(".ai-assistant");
      const responseBox = document.getElementById("ai-response");
      const question = document.getElementById("ai-question").value;
      button.disabled = true;
      responseBox.textContent = "Thinking…";
      try {
        const form = new FormData();
        form.append("action", button.dataset.aiAction);
        form.append("question", question);
        form.append("code", currentCode());
        const response = await fetch(root.dataset.url, {
          method: "POST",
          headers: { "X-CSRFToken": cookie("csrftoken") },
          body: form,
          credentials: "same-origin",
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "AI assistant is unavailable.");
        responseBox.textContent = result.answer;
      } catch (error) {
        responseBox.textContent = error.message || "AI assistant is unavailable.";
      } finally {
        button.disabled = false;
      }
    });
  });

  initializeMonaco();
})();
