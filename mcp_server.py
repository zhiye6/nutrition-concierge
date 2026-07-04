# mcp_server.py
import sqlite3
import asyncio
import json
import sys

def init_db():
    conn = sqlite3.connect("nutrition_diary.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_diary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT DEFAULT (date('now', 'localtime')),
            food_item TEXT, calories INTEGER, protein INTEGER, carbs INTEGER, sugar INTEGER
        )
    """)
    # Migration: Add water_oz if it does not exist
    try:
        cursor.execute("ALTER TABLE food_diary ADD COLUMN water_oz INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplement_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT DEFAULT (date('now', 'localtime')),
            supplement_name TEXT UNIQUE, is_taken INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn

db = init_db()

def validate_macro(val, name):
    if val is None or (isinstance(val, str) and not val.strip()):
        raise ValueError(f"{name.capitalize()} cannot be empty.")
    try:
        num = int(val)
    except (ValueError, TypeError):
        try:
            num = int(float(val))
        except (ValueError, TypeError):
            raise ValueError(f"{name.capitalize()} must be a valid integer.")
    if num < 0:
        raise ValueError(f"{name.capitalize()} cannot be negative.")
    return num

async def handle_tool_call(name, arguments):
    cursor = db.cursor()
    try:
        if name == "write_food_macros":
            food_item = arguments.get("food_item")
            if food_item is None or (isinstance(food_item, str) and not food_item.strip()):
                raise ValueError("Food item cannot be empty.")
            
            cals = validate_macro(arguments.get("calories"), "calories")
            prot = validate_macro(arguments.get("protein"), "protein")
            carbs = validate_macro(arguments.get("carbs"), "carbohydrates")
            sugar = validate_macro(arguments.get("sugar"), "sugar")
            water = validate_macro(arguments.get("water_oz"), "water")
            
            cursor.execute("""
                INSERT INTO food_diary (food_item, calories, protein, carbs, sugar, water_oz)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (food_item, cals, prot, carbs, sugar, water))
            db.commit()
            return f"Logged meal entry: {food_item}"
            
        elif name == "update_supplement_checklist":
            target = arguments.get("supplement_name", "")
            if target is None or (isinstance(target, str) and not target.strip()):
                raise ValueError("Supplement name cannot be empty.")
            target = target.strip().lower()
            is_taken = int(arguments.get("is_taken", 1))
            cursor.execute("INSERT INTO supplement_ledger (supplement_name, is_taken) VALUES (?, ?) ON CONFLICT(supplement_name) DO UPDATE SET is_taken=?", (target, is_taken, is_taken))
            db.commit()
            status_str = "taken" if is_taken == 1 else "missing"
            return f"Supplement marked as {status_str}: {arguments.get('supplement_name')}"
            
        elif name == "delete_food_entry":
            entry_id = arguments.get("id")
            if entry_id is None:
                raise ValueError("Entry ID is required.")
            try:
                entry_id = int(entry_id)
            except ValueError:
                raise ValueError("Entry ID must be an integer.")
            cursor.execute("DELETE FROM food_diary WHERE id = ?", (entry_id,))
            db.commit()
            return f"Deleted food diary entry ID: {entry_id}"
            
        elif name == "query_local_diary_db":
            cursor.execute("SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(sugar), SUM(water_oz) FROM food_diary WHERE log_date = date('now', 'localtime')")
            cals, prot, carb, sug, water = [v if v is not None else 0 for v in cursor.fetchone()]
            
            cursor.execute("SELECT id, food_item, calories, protein, carbs, sugar, water_oz FROM food_diary WHERE log_date = date('now', 'localtime')")
            entries = []
            for row in cursor.fetchall():
                entries.append({
                    "id": row[0],
                    "food_item": row[1],
                    "calories": row[2],
                    "protein": row[3],
                    "carbs": row[4],
                    "sugar": row[5],
                    "water_oz": row[6]
                })
            
            cursor.execute("SELECT supplement_name, is_taken FROM supplement_ledger WHERE log_date = date('now', 'localtime')")
            taken_dict = {row[0]: row[1] for row in cursor.fetchall()}
            
            import datetime
            now = datetime.datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            day_of_week = now.strftime("%A")
            
            supps = ["adult multivitamin", "fish oil", "apple cider vinegar", "d3", "joint health"]
            checklist = {}
            for s in supps:
                is_taken = taken_dict.get(s, 0)
                checklist[s] = "✅ Taken" if is_taken == 1 else "❌ Missing"
            
            return {
                "date": date_str,
                "day_of_week": day_of_week,
                "calories": cals,
                "protein": prot,
                "carbs": carb,
                "carbohydrates": carb,
                "sugar": sug,
                "water": water,
                "entries": entries,
                "checklist": checklist
            }
    except sqlite3.Error as e:
        error_code = getattr(e, "sqlite_errorcode", "N/A")
        error_name = getattr(e, "sqlite_errorname", "DatabaseError")
        raise RuntimeError(f"Database Transaction Failed ({error_name}, Code: {error_code}): {e}")

# Simplified standard JSON-RPC interface communication over stdio
async def main():
    while True:
        line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        try:
            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})
            
            if method == "call_tool":
                try:
                    result = await handle_tool_call(params.get("name"), params.get("arguments", {}))
                    sys.stdout.write(json.dumps({"result": result}) + "\n")
                except Exception as e:
                    sys.stdout.write(json.dumps({"error": {"message": str(e)}}) + "\n")
                sys.stdout.flush()
        except Exception as e:
            try:
                sys.stdout.write(json.dumps({"error": {"message": f"Server error: {e}"}}) + "\n")
                sys.stdout.flush()
            except Exception:
                pass

if __name__ == "__main__":
    asyncio.run(main())