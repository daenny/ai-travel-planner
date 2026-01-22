# Implementation Plan: Itinerary Update with Diff-Based Modifications

**Track ID:** itinerary_update_20260122
**Created:** 2026-01-22
**Status:** Complete

---

## Phase 1: Diff Data Models

Create the Pydantic models needed to represent itinerary changes.

- [x] Task: Write tests for FieldChange model [bf09c4e]
- [x] Task: Implement FieldChange model in models/itinerary.py [bf09c4e]
- [x] Task: Write tests for ActivityDiff model [9954ec6]
- [x] Task: Implement ActivityDiff model for activity-level changes [9954ec6]
- [x] Task: Write tests for DayDiff model [9758d9e]
- [x] Task: Implement DayDiff model for day-level changes [9758d9e]
- [x] Task: Write tests for ItineraryDiff model [de7f7a1]
- [x] Task: Implement ItineraryDiff container model with validation [de7f7a1]
- [x] Task: Conductor - User Manual Verification 'Phase 1: Diff Data Models' (Protocol in workflow.md) [348f7d5]

---

## Phase 2: Update Prompt and Agent Interface

Add the update prompt template and abstract method to the agent base class.

- [x] Task: Write tests for ITINERARY_UPDATE_PROMPT output parsing [89c47a5]
- [x] Task: Create ITINERARY_UPDATE_PROMPT template in agents/base.py [a4fbe12]
- [x] Task: Write tests for generate_itinerary_update abstract method signature [6f2341e]
- [x] Task: Add generate_itinerary_update() abstract method to TravelAgent base class [2c9720c]
- [x] Task: Conductor - User Manual Verification 'Phase 2: Update Prompt and Agent Interface' (Protocol in workflow.md) [1d2f176]

---

## Phase 3: Agent Implementations

Implement the update method for all three AI providers.

- [x] Task: Write tests for ClaudeAgent.generate_itinerary_update() [ae9a724]
- [x] Task: Implement generate_itinerary_update() in claude_agent.py [4a66ee8]
- [x] Task: Write tests for OpenAIAgent.generate_itinerary_update() [ae9a724]
- [x] Task: Implement generate_itinerary_update() in openai_agent.py [24fada7]
- [x] Task: Write tests for GeminiAgent.generate_itinerary_update() [ae9a724]
- [x] Task: Implement generate_itinerary_update() in gemini_agent.py [24fada7]
- [x] Task: Conductor - User Manual Verification 'Phase 3: Agent Implementations' (Protocol in workflow.md) [01540a4]

---

## Phase 4: Diff Application Service

Create the service to apply diffs and generate previews.

- [x] Task: Write tests for apply_diff function - add activity [5d3f3f3]
- [x] Task: Write tests for apply_diff function - remove activity [5d3f3f3]
- [x] Task: Write tests for apply_diff function - modify day [5d3f3f3]
- [x] Task: Write tests for apply_diff function - swap days [5d3f3f3]
- [x] Task: Write tests for apply_diff function - add/remove day [5d3f3f3]
- [x] Task: Implement apply_diff() in services/itinerary_updater.py [ab0525b]
- [x] Task: Write tests for preview_diff function [5d3f3f3]
- [x] Task: Implement preview_diff() for generating visual diff data [ab0525b]
- [x] Task: Write tests for validate_diff function [5d3f3f3]
- [x] Task: Implement validate_diff() to verify diff is applicable [ab0525b]
- [x] Task: Conductor - User Manual Verification 'Phase 4: Diff Application Service' (Protocol in workflow.md) [0a307fb]

---

## Phase 5: UI Integration

Add diff visualization components to the Streamlit Itinerary tab.

- [x] Task: Design diff visualization component layout [47d1eac]
- [x] Task: Implement DiffPreviewComponent showing additions/removals/modifications [47d1eac]
- [x] Task: Implement Accept/Reject buttons with session state management [47d1eac]
- [x] Task: Integrate update flow into Itinerary tab [47d1eac]
- [x] Task: Add "Update Itinerary" button to trigger update mode [47d1eac]
- [x] Task: Connect chat-based update requests to diff preview [47d1eac]
- [x] Task: Conductor - User Manual Verification 'Phase 5: UI Integration' (Protocol in workflow.md) [2221ecd]

---

## Phase 6: End-to-End Testing and Polish

Final integration testing and user experience refinements.

- [x] Task: Write end-to-end test for complete update flow [e4f0bcf]
- [x] Task: Test update flow with Claude provider [e4f0bcf]
- [x] Task: Test update flow with OpenAI provider [e4f0bcf]
- [x] Task: Test update flow with Gemini provider [e4f0bcf]
- [x] Task: Add error handling for malformed diff responses
- [x] Task: Add user-friendly error messages for invalid updates
- [x] Task: Update CLAUDE.md with update feature documentation
- [x] Task: Conductor - User Manual Verification 'Phase 6: End-to-End Testing and Polish' (Protocol in workflow.md)

---

## Notes

- All tasks follow TDD workflow: write failing tests first, then implement
- Each task should be committed separately with git notes
- Phase completion triggers the verification protocol in workflow.md
