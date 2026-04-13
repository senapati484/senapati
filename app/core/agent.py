import os
import json
import logging
import threading
import time
import platform
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core import brain, voice_in, voice_out
from app.prompts import (
    build_system_prompt,
    build_tool_prompt,
    build_approval_prompt,
    build_ocr_prompt,
    build_context_bridge_prompt,
    build_error_recovery_prompt,
    build_onboarding_prompt,
    build_fact_extraction_prompt,
    build_session_summary_prompt,
    parse_json_response,
    FEW_SHOT_EXAMPLES,
)

logger = logging.getLogger(__name__)

SENAPATI_HOME = os.path.expanduser("~/.senapati")
CONFIG_PATH = os.path.join(SENAPATI_HOME, "config.json")

AgentState = {
    "idle": "idle",
    "listening": "listening",
    "thinking": "thinking",
    "speaking": "speaking",
    "error": "error",
    "muted": "muted",
}


class Agent:
    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = config_path
        self.config = self._load_config()
        
        self.state = "idle"
        self.session_id = None
        self.session_start = None
        self.turn_count = 0
        self.session_history: List[Dict[str, str]] = []
        
        self._action_log: List[Dict[str, Any]] = []
        self._pending_approval = None
        self._onboarding_done = self.config.get("onboarded", False)
        
        self.muted = False
        self.trusted_mode = self.config.get("safety", {}).get("trusted_mode", False)
        
        self._callbacks: Dict[str, callable] = {}
    
    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path) as f:
                    return json.load(f)
            except:
                pass
        return {"name": "Senapati", "onboarded": False}
    
    def _save_config(self) -> None:
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except:
            pass
    
    def start(self) -> None:
        """Start the agent daemon."""
        logger.info("Starting Senapati...")
        
        brain.reload_if_needed()
        
        if not self.muted:
            voice_in.listen_for_wake(on_wake_detected=self._on_wake)
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = time.time()
        
        self._set_state("idle")
        
        # Start menu bar on macOS (shared state dict)
        if platform.system() == "Darwin":
            from app.bridges import menubar
            menubar.start_menubar(self._agent_state)
        
        logger.info("Senapati started")
        
        # PROMPT_10: Check for proactive habit suggestions
        self._check_habits()
        
        # PROMPT_13: Check for unconfigured plugins
        self._check_plugins()
    
    @property
    def _agent_state(self) -> Dict[str, Any]:
        """Shared state dict for menu bar."""
        return {
            "state": self.state,
            "muted": self.muted,
            "trusted_mode": self.trusted_mode,
        }
    
    def _check_plugins(self) -> None:
        """PROMPT_13: Check and prompt for unconfigured plugins."""
        import os
        import glob
        
        plugins_dir = os.path.expanduser("~/.senapati/plugins")
        
        if not os.path.exists(plugins_dir):
            return
        
        plugin_files = glob.glob(os.path.join(plugins_dir, "*_mcp.py"))
        
        if not plugin_files:
            return
        
        config = self.config.get("plugins", {})
        
        for plugin_path in plugin_files:
            plugin_name = os.path.basename(plugin_path).replace("_mcp.py", "")
            
            if config.get(plugin_name, {}).get("enabled", False):
                continue
            
            plugin_descriptions = {
                "telegram": "Send and receive Telegram messages",
                "github": "Check GitHub notifications and PRs",
                "spotify": "Control Spotify playback",
            }
            
            prompt = build_plugin_setup_prompt(
                plugin_name=plugin_name,
                plugin_file=plugin_path,
                required_keys="bot_token or api_key",
                plugin_desc=plugin_descriptions.get(plugin_name, "Custom plugin"),
            )
            
            response = brain.generate(prompt, max_tokens=128)
            data = parse_json_response(response)
            
            speak = data.get("speak", "")
            if speak:
                self._set_state("speaking")
                voice_out.speak(speak)
                break
    
    def _check_habits(self) -> None:
        """PROMPT_10: Check and suggest habits."""
        from datetime import datetime
        from app.memory import store
        
        now = datetime.now()
        weekday = now.strftime("%A")
        hour = now.hour
        current_time = now.strftime("%I:%M %p")
        
        habits = store.get_habits(weekday, hour)
        
        if not habits:
            return
        
        habit = habits[0]
        
        user_name = self.config.get("name", "there")
        
        prompt = build_habit_suggest_prompt(
            user_name=user_name,
            habit_tool=habit["tool"],
            habit_args=habit["args"],
            habit_count=habit["count"],
            habit_weekday=weekday,
            habit_hour=hour,
            current_time=current_time,
        )
        
        response = brain.generate(prompt, max_tokens=64)
        data = parse_json_response(response)
        
        speak = data.get("speak", "")
        if speak:
            self._set_state("speaking")
            voice_out.speak(speak)
    
    def stop(self) -> None:
        """Stop the agent."""
        logger.info("Stopping Senapati...")
        
        # PROMPT_7 + PROMPT_11: Extract facts and summarize session
        self._end_session()
        
        voice_in.stop_listening()
        
        self._save_config()
        self._set_state("idle")
        logger.info("Senapati stopped")
    
    def _end_session(self) -> None:
        """PROMPT_7 + PROMPT_11: End session with fact extraction and summary."""
        if not self.session_history:
            return
        
        # Get full conversation
        conversation = []
        for turn in self.session_history:
            role = turn.get("role", "?")
            content = turn.get("content", "")
            conversation.append(f"{role}: {content}")
        
        full_text = "\n".join(conversation)
        
        # PROMPT_7: Extract facts from conversation
        from app.prompts import build_fact_extraction_prompt
        fact_prompt = build_fact_extraction_prompt(full_text)
        
        try:
            fact_response = brain.generate(fact_prompt, max_tokens=256)
            fact_data = parse_json_response(fact_response)
            
            # Save extracted facts
            if isinstance(fact_data, list):
                from app.memory import store
                for fact in fact_data:
                    category = fact.get("category", "fact")
                    content = fact.get("content", "")
                    confidence = fact.get("confidence", 0.8)
                    if content:
                        store.save_fact(category, content, confidence)
        except Exception as e:
            logger.error(f"Fact extraction failed: {e}")
        
        # PROMPT_11: Generate session summary
        from app.prompts import build_session_summary_prompt
        from datetime import datetime
        
        summary_prompt = build_session_summary_prompt(
            full_session_text=full_text,
            session_date=self.session_id[:8] if self.session_id else datetime.now().strftime("%Y%m%d"),
            session_duration=f"{int(time.time() - self.session_start)}s" if self.session_start else "0s",
        )
        
        try:
            summary_response = brain.generate(summary_prompt, max_tokens=128)
            summary_data = parse_json_response(summary_response)
            
            summary_text = summary_data.get("speak", "")[:500]
            
            # Save to store
            from app.memory import store
            if self.session_id:
                store.close_session(self.session_id, summary=summary_text)
        except Exception as e:
            logger.error(f"Session summary failed: {e}")
    
    def _on_wake(self) -> None:
        """Called when wake word is detected."""
        if self.muted:
            return
        
        # Barge-in: stop any ongoing speech
        if self.state == "speaking":
            voice_out.request_barge_in()
            import time
            time.sleep(0.1)
        
        self._set_state("listening")
        
        # PROMPT_0: Immediate wake acknowledgment (no LLM call - synchronous)
        ack_text = self._get_wake_ack_immediate()
        if ack_text:
            # Fire acknowledgment immediately - doesn't wait for STT
            voice_out.speak_immediately(ack_text)
        
        # Start audio recording in background while acknowledging
        # This runs PROMPT_1 + PROMPT_2 in parallel
        audio_path = voice_in.record_audio(duration=5.0)
        if audio_path:
            user_input = voice_in.transcribe(audio_path)
            if user_input:
                self._process_input(user_input)
    
    def _get_wake_ack_immediate(self) -> str:
        """PROMPT_0: Get immediate wake acknowledgment (no LLM - instant)."""
        import random
        from datetime import datetime
        
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            morning_opts = ["Morning!", "Good morning", "Rise and shine", "Hey"]
        elif 12 <= hour < 17:
            afternoon_opts = ["Yeah?", "Go ahead", "What's up"]
        elif 17 <= hour < 21:
            evening_opts = ["Evening", "Hey", "What's up"]
        else:
            late_opts = ["Late night", "Hey", "Still up?"]
        
        opts = morning_opts if 5 <= hour < 12 else (
            afternoon_opts if 12 <= hour < 17 else (
                evening_opts if 17 <= hour < 21 else late_opts
            )
        )
        
        return random.choice(opts)
    
    def _get_wake_ack(self) -> str:
        """PROMPT_0: Full LLM-based wake acknowledgment (slower)."""
        from app.prompts import build_wake_ack_prompt
        
        prompt = build_wake_ack_prompt(
            user_name=self.config.get("name", "there")
        )
        
        response = brain.generate(prompt, max_tokens=10)
        try:
            data = parse_json_response(response)
            return data.get("speak", "Yeah?")[:50]
        except:
            return "Yeah?"
    
    def _process_input(self, user_input: str) -> None:
        """Process user input - PROMPT_1 + PROMPT_2 chain."""
        # PROMPT_9: First-run onboarding check
        if not self._onboarding_done:
            self._do_onboarding()
            self._onboarding_done = True
            self.config["onboarded"] = True
            self._save_config()
        
        self._set_state("thinking")
        
        # PROMPT_15: Resolve ambiguous references
        resolved_input = self._resolve_references(user_input)
        
        # Get all memory context
        memory_context = self._get_memory_context()
        pending_tasks = self._get_pending_tasks()
        user_facts = self._get_user_facts()
        session_history = self._format_history()
        uptime = self._get_uptime()
        
        # PROMPT_1: Core system prompt with full context
        system_prompt = build_system_prompt(
            user_name=self.config.get("name", "there"),
            memory_context=memory_context,
            session_history=session_history,
            turn_count=self.turn_count,
            pending_tasks=pending_tasks,
            user_facts=user_facts,
            uptime=uptime,
        )
        
        # PROMPT_2: Tool routing (in brain.think)
        response = brain.think(
            user_input=resolved_input,
            system_prompt=system_prompt,
            memory_context=memory_context,
            session_history=session_history,
        )
        
        self._handle_response(response)
        
        self.session_history.append({
            "role": "user",
            "content": user_input,
        })
        self.turn_count += 1
    
    def _resolve_references(self, user_input: str) -> str:
        """Resolve ambiguous references."""
        ambiguous = {"that", "it", "they", "them", "the one", "that file", "the project"}
        
        if not any(word in user_input.lower() for word in ambiguous):
            return user_input
        
        prompt = build_context_bridge_prompt(
            user_input=user_input,
            session_history=self._format_history(limit=4),
            memory_entities="",
        )
        
        response = brain.generate(prompt, max_tokens=128)
        resolved = response.strip()
        
        if resolved and resolved != user_input:
            logger.info(f"Resolved: {user_input} → {resolved}")
            return resolved
        
        return user_input
    
    def _handle_response(self, response: Dict[str, Any]) -> None:
        """Handle agent response."""
        if not response:
            return
        
        tool = response.get("tool", "chat")
        speak = response.get("speak", "")
        
        # PROMPT_3: Approval gate for destructive/risky actions
        if tool == "request_approval":
            action_desc = response.get("args", {}).get("action", "")
            risk_level = response.get("args", {}).get("risk", "medium")
            
            # Generate natural approval request using PROMPT_3
            approval_prompt = build_approval_prompt(action_desc, risk_level)
            approval_response = brain.generate(approval_prompt, max_tokens=32)
            approval_text = approval_response.strip()
            
            self._pending_approval = {
                "tool": response.get("args", {}).get("execute_tool", "run_shell"),
                "args": response.get("args", {}),
            }
            
            self._set_state("speaking")
            voice_out.speak(approval_text)
        
        elif tool == "run_shell":
            args = response.get("args", {})
            
            # Shell commands require approval (unless trusted mode)
            if args.get("require_approval", False) and not self.trusted_mode:
                action_desc = args.get("command", "run shell command")
                risk_level = "high" if "rm" in action_desc or "delete" in action_desc else "medium"
                
                # PROMPT_3: Generate approval request
                approval_prompt = build_approval_prompt(action_desc, risk_level)
                approval_response = brain.generate(approval_prompt, max_tokens=32)
                approval_text = approval_response.strip()
                
                self._pending_approval = {
                    "tool": "run_shell",
                    "args": args,
                }
                
                self._set_state("speaking")
                voice_out.speak(approval_text)
            else:
                # Execute directly in trusted mode
                self._execute_tool("run_shell", args)
                self._log_action("run_shell", args)
                
                self._set_state("speaking")
                if speak:
                    voice_out.speak(speak)
        
        elif tool == "open_app":
            self._execute_tool("open_app", response.get("args", {}))
            self._log_action("open_app", response.get("args", {}))
            
            self._set_state("speaking")
            if speak:
                voice_out.speak(speak)
        
        elif tool == "read_screen":
            self._set_state("speaking")
            voice_out.speak("Let me check your screen.")
            
            ocr_text = self._read_screen()
            
            ocr_prompt = build_ocr_prompt(
                user_question="What does my screen show?",
                ocr_text=ocr_text,
            )
            
            ocr_response = brain.generate(ocr_prompt, max_tokens=128)
            ocr_data = parse_json_response(ocr_response)
            
            speak = ocr_data.get("speak", "Couldn't read that.")
            self._set_state("speaking")
            voice_out.speak(speak)
        
        elif tool == "chat":
            self._set_state("speaking")
            if speak:
                voice_out.speak(speak)
        
        # PROMPT_6: Multi-step execution
        if "steps" in response:
            steps = response.get("steps", [])
            self._handle_steps(steps)
            return
        
        self.session_history.append({
            "role": "assistant",
            "content": json.dumps(response),
        })
    
    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a tool - PROMPT_8 on failure."""
        from app.tools import system_mcp, file_mcp, dev_mcp, vision_mcp
        
        tools = {
            "open_app": system_mcp.open_app,
            "close_app": system_mcp.close_app,
            "get_system_stats": system_mcp.get_system_stats,
            "set_volume": system_mcp.set_volume,
            "run_shell": system_mcp.run_shell,
            "search_files": file_mcp.search_files,
            "read_file": file_mcp.read_file,
            "write_file": file_mcp.write_file,
            "move_file": file_mcp.move_file,
            "summarize_folder": file_mcp.summarize_folder,
            "git_status": dev_mcp.git_status,
            "git_log": dev_mcp.git_log,
            "run_dev_server": dev_mcp.run_dev_server,
            "open_in_editor": dev_mcp.open_in_editor,
            "read_screen": vision_mcp.read_screen,
            "find_text_on_screen": vision_mcp.find_text_on_screen,
        }
        
        tool_func = tools.get(tool_name)
        
        if tool_func:
            try:
                return tool_func(**args)
            except Exception as e:
                # PROMPT_8: Error recovery
                return self._handle_error(tool_name, args, e)
        
        return f"Tool {tool_name} not found"
    
    def _handle_error(self, tool_name: str, args: Dict[str, Any], error: Exception) -> str:
        """PROMPT_8: Handle tool error with natural recovery."""
        import traceback
        
        error_type = type(error).__name__
        error_message = str(error)
        
        # Check for retry condition (JSON decode error)
        if "JSONDecodeError" in error_type:
            return "I got confused — try saying that again."
        
        # Build error recovery prompt
        prompt = build_error_recovery_prompt(
            tool_name=tool_name,
            tool_args=args,
            error_type=error_type,
            error_message=error_message[:200],
        )
        
        try:
            response = brain.generate(prompt, max_tokens=64)
            data = parse_json_response(response)
            return data.get("speak", f"Something went wrong: {error_message[:50]}")
        except:
            return f"Something went wrong: {error_message[:50]}"
    
    def _handle_steps(self, steps: list) -> None:
        """PROMPT_6: Execute multi-step task."""
        for i, step in enumerate(steps):
            tool = step.get("tool")
            args = step.get("args", {})
            step_speak = step.get("speak", "")
            
            # Execute step
            result = self._execute_tool(tool, args)
            
            # Speak confirmation for each step (except last)
            if i < len(steps) - 1:
                self._set_state("speaking")
                if step_speak:
                    voice_out.speak(step_speak)
        
        # Final summary
        final_speak = steps[-1].get("speak", "Done.") if steps else "Done."
        self._set_state("speaking")
        voice_out.speak(final_speak)
    
    def _read_screen(self) -> str:
        """Read screen with OCR."""
        from app.tools import vision_mcp
        
        try:
            return vision_mcp.read_screen()
        except Exception as e:
            logger.error(f"Screen read failed: {e}")
            return ""
    
    def _log_action(self, tool: str, args: Dict[str, Any]) -> None:
        """Log action for undo + habit detection (PROMPT_10)."""
        self._action_log.append({
            "tool": tool,
            "args": args,
            "timestamp": time.time(),
        })
        
        # PROMPT_10: Record habit pattern
        from datetime import datetime
        try:
            from app.memory import store
            now = datetime.now()
            store.record_habit(
                tool=tool,
                args_json=json.dumps(args),
                weekday=now.strftime("%A"),
                hour=now.hour,
            )
        except Exception as e:
            logger.debug(f"Habit recording skipped: {e}")
    
    def _get_memory_context(self) -> str:
        """Get memory context."""
        from app.memory import retrieval
        
        try:
            return retrieval.retrieve_context("", limit=5)
        except:
            return ""
    
    def _get_pending_tasks(self) -> str:
        """Get pending tasks summary."""
        from app.memory import retrieval
        
        try:
            return retrieval.get_pending_tasks_summary()
        except:
            return "(no pending tasks)"
    
    def _get_user_facts(self) -> str:
        """Get user facts summary."""
        from app.memory import retrieval
        
        try:
            return retrieval.get_user_facts_summary()
        except:
            return "(no facts known)"
    
    def _get_uptime(self) -> str:
        """Get agent uptime."""
        if self.session_start:
            import time
            seconds = int(time.time() - self.session_start)
            minutes = seconds // 60
            hours = minutes // 60
            
            if hours > 0:
                return f"{hours}h {minutes % 60}m"
            elif minutes > 0:
                return f"{minutes}m"
            else:
                return f"{seconds}s"
        return "0m"
    
    def _do_onboarding(self) -> None:
        """PROMPT_9: First-run onboarding."""
        import platform
        from datetime import datetime
        
        user_name = self.config.get("name", "there")
        os_name = platform.system()
        
        hour = datetime.now().hour
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"
        
        # PROMPT_9: Generate onboarding
        from datetime import datetime as dt
        prompt = build_onboarding_prompt(
            user_name=user_name,
            os_name=os_name,
            time_of_day=time_of_day,
        )
        
        response = brain.generate(prompt, max_tokens=100)
        data = parse_json_response(response)
        
        speak = data.get("speak", "Hey, I'm Senapati — your local AI assistant.")
        
        self._set_state("speaking")
        voice_out.speak(speak)
    
    def _format_history(self, limit: int = 6) -> str:
        """Format session history."""
        if not self.session_history:
            return "(no prior turns)"
        
        lines = []
        for turn in self.session_history[-limit:]:
            role = turn.get("role", "?")
            content = turn.get("content", "")[:100]
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    def _set_state(self, state: str) -> None:
        """Set agent state."""
        self.state = state
        
        if state == "speaking":
            self.state = "idle"
    
    def approve_last_action(self) -> bool:
        """User approved - execute pending action."""
        if not self._pending_approval:
            return False
        
        response = self._pending_approval
        tool = response.get("tool")
        args = response.get("args", {})
        
        # Execute the pending action
        result = self._execute_tool(tool, args)
        self._log_action(tool, args)
        
        self._set_state("speaking")
        voice_out.speak(result or "Done.")
        
        self._pending_approval = None
        return True
    
    def deny_last_action(self) -> None:
        """User denied - cancel pending action."""
        if not self._pending_approval:
            return
        
        self._set_state("spaking")
        voice_out.speak("Got it. Cancelled.")
        
        self._pending_approval = None
        
        self._pending_approval = None
    
    def toggle_mute(self) -> None:
        """Toggle mute."""
        self.muted = not self.muted
        self._set_state("idle" if self.muted else "listening")
    
    def toggle_trusted(self) -> None:
        """Toggle trusted mode."""
        self.trusted_mode = not self.trusted_mode
        self.config.setdefault("safety", {})["trusted_mode"] = self.trusted_mode
        self._save_config()
    
    def handle_undo(self) -> bool:
        """Undo last action - PROMPT_14."""
        if not self._action_log:
            return False
        
        if len(self._action_log) < 3:
            recent_log = json.dumps(self._action_log[-3:])
        else:
            recent_log = json.dumps(self._action_log[-3:])
        
        last = self._action_log[-1]
        
        prompt = build_undo_prompt(
            recent_actions=recent_log,
            last_tool=last.get("tool", ""),
            last_args=last.get("args", {}),
            last_result="",
            last_timestamp=datetime.fromtimestamp(last.get("timestamp", 0)).isoformat(),
        )
        
        response = brain.generate(prompt, max_tokens=64)
        data = parse_json_response(response)
        
        tool = data.get("tool")
        args = data.get("args", {})
        speak = data.get("speak", "Can't undo that.")
        
        if tool and tool != "chat":
            self._execute_tool(tool, args)
            self._action_log.pop()
        
        self._set_state("speaking")
        voice_out.speak(speak)
        
        return True
    
    def run_morning_brief(self) -> str:
        """Generate morning brief."""
        from app.brief import morning
        
        try:
            brief_text = morning.generate_brief(
                user_name=self.config.get("name", "there")
            )
            
            self._set_state("speaking")
            voice_out.speak(brief_text)
            
            return brief_text
        
        except Exception as e:
            logger.error(f"Morning brief failed: {e}")
            return str(e)
    
    def on(self, event: str, callback: callable) -> None:
        """Register callback."""
        self._callbacks[event] = callback
    
    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit event."""
        callback = self._callbacks.get(event)
        if callback:
            callback(*args, **kwargs)


_default_agent: Optional[Agent] = None


def get_agent() -> Agent:
    """Get default agent instance."""
    global _default_agent
    
    if _default_agent is None:
        _default_agent = Agent()
    
    return _default_agent


def start_daemon() -> None:
    """Start daemon mode."""
    agent = get_agent()
    agent.start()


def run_brief() -> str:
    """Run morning brief."""
    agent = get_agent()
    return agent.run_morning_brief()