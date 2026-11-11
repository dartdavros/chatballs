export const skillsEn = {
  "skills.delete_action": "Delete skill",
  "skills.created": "created {date}",
  "skills.field_list": "list",
  "skills.field_count": {
    "one": "{count} field",
    "other": "{count} fields"
  },
  "skills.optional_count": {
    "one": "{count} optional",
    "other": "{count} optional"
  },
  "shared.clear_search": "Clear search",
  "skills.html_css": "HTML and CSS",
  "skills.text_version": "Text version",
  "skills.title": "Skills",
  "skills.agent_list": "Agent list",
  "skills.lead": "Skills are shared instructions and response templates. Connect them to any agent in the organization.",
  "skills.create": "Create skill",
  "skills.search": "Search names and descriptions…",
  "skills.skill": "Skill",
  "skills.templates": "Response templates",
  "skills.agents": "Connected agents",
  "skills.updated": "Updated",
  "skills.instruction_only": "Instructions only",
  "skills.unattached": "Not connected",
  "skills.empty": "No skills in the library yet",
  "skills.empty_help": "A skill guides an agent through a particular type of request and can include response templates. One skill can connect to several agents.",
  "skills.loading": "Loading library…",
  "skills.not_found": "Skill not found",
  "skills.no_results": "Nothing found",
  "skills.managers": "Owners and administrators create and edit skills.",
  "skills.basis": "Basis",
  "skills.blank": "New skill",
  "skills.orders": "Working with orders",
  "skills.replace": "Replace entered data?",
  "skills.replace_action": "Replace",
  "skills.main": "Basics",
  "skills.name": "Name",
  "skills.description": "When to use",
  "skills.instruction": "Instructions",
  "skills.description_hint": "The agent reads this description to decide whether the skill is needed. Be specific.",
  "skills.instruction_hint": "Detailed rules: steps to follow, what to do when information is missing, and when to involve an employee.",
  "skills.required": "Fill in this required field",
  "skills.too_long": "Maximum {count} characters",
  "skills.templates_hint": "Optional. With a template the agent sends a formatted message; without one it follows the instructions in plain text.",
  "skills.add_template": "Add template",
  "skills.ordinary": "The agent responds in plain text",
  "skills.ordinary_hint": "This is enough for conversational guidance. A response template can be added later.",
  "skills.template_unavailable": "The template editor is not available yet",
  "skills.connect_hint": "Connect and disconnect in the Skills section of the agent card.",
  "skills.no_agents": "No agents yet. The skill can be connected after saving.",
  "skills.bounds": "Skill boundaries",
  "skills.bounds_rights": "Does not grant new permissions or tools. The agent gets data, such as orders, only through its connections.",
  "skills.bounds_style": "Formatting applies inside the message and does not change the rest of the widget.",
  "skills.bounds_history": "Changes apply to new messages. Messages already sent remain unchanged.",
  "skills.unsaved": "Unsaved changes",
  "skills.leave": "Save skill changes?",
  "skills.leave_hint": "There are unsaved changes. They will be lost if you leave.",
  "skills.discard": "Discard",
  "skills.stay": "Stay",
  "skills.reset": "Revert changes",
  "skills.action_error": "The action failed. Your changes remain on screen. Try again.",
  "skills.conflict": "Another employee changed this skill. Refresh the data before saving.",
  "skills.refresh": "Refresh data",
  "skills.delete_title": "Delete skill “{name}”?",
  "skills.delete_hint": "The skill and its templates will be removed from the library. Sent messages will not change.",
  "skills.card_hint": "The agent selects skills by description. Skills are shared and edited in the library.",
  "skills.connect": "Connect skill",
  "skills.library": "In library",
  "skills.disconnect": "Disconnect",
  "skills.none": "No skills connected — the agent follows its own instructions.",
  "skills.shared_hint": "Library edits apply to all connected agents. Disconnecting here affects only “{name}”. Skills grant no new permissions or tools.",
  "skills.connect_title": "Connect skills to “{name}”",
  "skills.connect_lead": "Skills come from the shared organization library.",
  "skills.already": "Already connected",
  "skills.disconnect_title": "Disconnect “{name}”?",
  "skills.disconnect_hint": "Agent “{name}” will stop using this skill in new responses. The skill remains in the library and with other agents.",
  "skills.unsupported": "This model does not support skills. Select a model that supports tool calls.",
  "skills.unknown": "Skill support for this model is unknown.",
  "skills.used": {
    "one": "Connected to {count} agent",
    "other": "Connected to {count} agents"
  },
  "skills.save_for": {
    "one": "Save for {count} agent",
    "other": "Save for {count} agents"
  },
  "skills.affected": {
    "one": "Changes will affect {count} agent.",
    "other": "Changes will affect {count} agents."
  },
  "skills.delete_agents": {
    "one": "{count} agent will lose this skill:",
    "other": "{count} agents will lose this skill:"
  },
  "skills.template_count": {
    "one": "{count} template",
    "other": "{count} templates"
  },
  "skills.connect_count": {
    "one": "Connect {count} skill",
    "other": "Connect {count} skills"
  },
  "skills.total": {
    "one": "{count} skill",
    "other": "{count} skills"
  }
} as const;
