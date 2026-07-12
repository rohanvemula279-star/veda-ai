import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


class PluginManager:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.plugins_dir = self.base_dir / "plugins"
        self.config_path = self.base_dir / "config" / "plugins_config.json"
        self.plugins: list[Any] = []
        self.plugin_records: dict[str, dict[str, Any]] = {}
        self.veda_ai = None
        self._enabled_state: dict[str, bool] = self._load_config()

    def _load_config(self) -> dict[str, bool]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Plugins] Config read error: {e}")
        return {}

    def _save_config(self) -> None:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._enabled_state, f, indent=2)
        except Exception as e:
            print(f"[Plugins] Config save error: {e}")

    def load_plugins(self) -> None:
        if not self.plugins_dir.exists():
            return
        self.plugins.clear()
        self.plugin_records.clear()

        for p in sorted(self.plugins_dir.glob("*.py")):
            if p.name.startswith("__"):
                continue
            plugin_id = p.stem
            try:
                spec = importlib.util.spec_from_file_location(plugin_id, str(p))
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                sys.modules[plugin_id] = mod
                spec.loader.exec_module(mod)
                plugin = getattr(mod, "plugin", None)
                if plugin is None:
                    plugin = mod

                # Extract metadata
                name = getattr(plugin, "NAME", plugin_id.replace("_", " ").title())
                desc = getattr(plugin, "DESCRIPTION", "Plugin for Veda AI")
                ver = getattr(plugin, "VERSION", "1.0.0")
                author = getattr(plugin, "AUTHOR", "Veda AI")
                icon = getattr(plugin, "ICON", "🔌")
                cat = getattr(plugin, "CATEGORY", "General")
                prompts = getattr(plugin, "SAMPLE_PROMPTS", [])
                enabled = self._enabled_state.get(plugin_id, True)

                record = {
                    "id": plugin_id,
                    "name": name,
                    "description": desc,
                    "version": ver,
                    "author": author,
                    "icon": icon,
                    "category": cat,
                    "sample_prompts": prompts,
                    "enabled": enabled,
                    "instance": plugin,
                }
                self.plugin_records[plugin_id] = record
                self.plugins.append(plugin)
                print(f"[Plugins] Loaded {p.name} ('{name}') - Enabled: {enabled}")
            except Exception as exc:
                print(f"[Plugins] Failed to load {p.name}: {exc}")

    def register_veda(self, veda_obj) -> None:
        self.veda_ai = veda_obj
        for pid, record in self.plugin_records.items():
            if not record.get("enabled", True):
                continue
            p = record["instance"]
            try:
                fn = getattr(p, "on_veda_created", None)
                if callable(fn):
                    fn(veda_obj)
            except Exception as exc:
                print(f"[Plugins] on_veda_created error in {pid}: {exc}")

    def get_plugins_metadata(self) -> List[Dict[str, Any]]:
        meta_list = []
        for pid, rec in self.plugin_records.items():
            meta_list.append({
                "id": rec["id"],
                "name": rec["name"],
                "description": rec["description"],
                "version": rec["version"],
                "author": rec["author"],
                "icon": rec["icon"],
                "category": rec["category"],
                "sample_prompts": rec["sample_prompts"],
                "enabled": rec.get("enabled", True),
            })
        return meta_list

    def toggle_plugin(self, plugin_id: str, enabled: bool) -> bool:
        if plugin_id in self.plugin_records:
            self.plugin_records[plugin_id]["enabled"] = enabled
            self._enabled_state[plugin_id] = enabled
            self._save_config()
            return True
        return False

    def dispatch(self, hook: str, *args, **kwargs):
        """Call hook on enabled plugins. If any plugin returns True, stop and return True."""
        for pid, rec in list(self.plugin_records.items()):
            if not rec.get("enabled", True):
                continue
            p = rec["instance"]
            try:
                fn = getattr(p, hook, None)
                if callable(fn):
                    call_kwargs = dict(kwargs)
                    call_kwargs.setdefault("veda_ai", self.veda_ai)
                    call_kwargs.setdefault("veda_echo", self.veda_ai)
                    try:
                        res = fn(*args, **call_kwargs)
                    except TypeError:
                        try:
                            res = fn(*args, **kwargs, veda_echo=self.veda_ai)
                        except TypeError:
                            res = fn(*args, **kwargs)
                    if res is True:
                        return True
            except Exception as exc:
                print(f"[Plugins] Hook {hook} error in {pid}: {exc}")
        return False

