# Specification: Itinerary Update with Diff-Based Modifications

## Overview

This feature enables users to update existing itineraries through natural language conversation, using diff-based modifications instead of regenerating the entire itinerary. This approach minimizes AI output token usage and provides visual diff-views so users can see exactly what changed.

## Problem Statement

Currently, when users want to modify an existing itinerary (e.g., "swap day 3 and day 4" or "add a restaurant recommendation to the evening of day 2"), the system must regenerate the entire itinerary. This has several drawbacks:

1. **Token Inefficiency**: Regenerating a 10-day itinerary uses 10x the tokens needed for a single day change
2. **Risk of Unintended Changes**: Full regeneration may subtly alter other parts of the itinerary
3. **No Change Visibility**: Users cannot easily see what changed between versions
4. **Slow Feedback**: Regeneration takes longer than targeted updates

## Solution

Implement a diff-based update system that:

1. Accepts natural language update requests ("Add a beach day on day 5")
2. Generates only the changes as a structured diff format
3. Applies the diff to the existing itinerary
4. Displays a visual diff-view showing additions, removals, and modifications

## User Stories

### US-1: Update Itinerary via Chat
As a user, I want to request itinerary changes through the chat interface (e.g., "Move the temple visit from day 2 to day 3") so that I can refine my trip plan conversationally.

### US-2: View Changes Before Applying
As a user, I want to see what will change before accepting an update so that I can verify the AI understood my request correctly.

### US-3: Accept or Reject Changes
As a user, I want to accept or reject proposed changes so that I maintain control over my itinerary.

### US-4: View Change History
As a user, I want to see a summary of what changed after an update is applied so that I can track how my itinerary evolved.

## Functional Requirements

### FR-1: Diff Data Model
Create Pydantic models to represent itinerary changes:
- `ItineraryDiff`: Container for all changes to an itinerary
- `DayDiff`: Changes to a specific day (add, remove, modify)
- `ActivityDiff`: Changes to a specific activity
- `FieldChange`: Generic field-level change (old_value, new_value)

### FR-2: Update Prompt Template
Create a new prompt template (`ITINERARY_UPDATE_PROMPT`) that:
- Takes the current itinerary state as context
- Accepts a natural language update request
- Returns a structured diff JSON (not a full itinerary)
- Includes examples of various update types

### FR-3: TravelAgent Update Method
Add `generate_itinerary_update()` method to the `TravelAgent` base class:
- Input: current itinerary, update request, language
- Output: `ItineraryDiff` object
- Must be implemented by all agent subclasses (Claude, OpenAI, Gemini)

### FR-4: Diff Application Service
Create `itinerary_updater.py` service with:
- `apply_diff(itinerary: Itinerary, diff: ItineraryDiff) -> Itinerary`: Applies changes
- `preview_diff(itinerary: Itinerary, diff: ItineraryDiff) -> DiffPreview`: Generates preview
- Validation to ensure diff is applicable (e.g., day exists, activity exists)

### FR-5: Diff Visualization Component
Create Streamlit components for the Itinerary tab:
- Visual diff display showing additions (green), removals (red), modifications (yellow)
- Side-by-side or inline diff view options
- Accept/Reject buttons for pending changes
- Collapsible sections for each changed day

### FR-6: Chat Integration
Integrate update functionality into the chat flow:
- Detect update intent when itinerary exists
- Show diff preview in the chat or Itinerary tab
- Provide "Apply Changes" action button

## Non-Functional Requirements

### NFR-1: Token Efficiency
Updates should use significantly fewer tokens than full regeneration:
- Single day change: <20% of full generation tokens
- Multi-day change: <40% of full generation tokens

### NFR-2: Change Accuracy
The diff must accurately reflect the user's intent:
- Only requested changes should appear in the diff
- Unrelated days/activities must remain unchanged

### NFR-3: UI Responsiveness
Diff preview should render within 500ms after receiving AI response.

## Technical Design

### Diff JSON Structure

```json
{
  "summary": "Added beach activity to Day 3, swapped Days 4 and 5",
  "changes": [
    {
      "type": "modify_day",
      "day_number": 3,
      "changes": {
        "activities": {
          "add": [
            {
              "position": 2,
              "activity": { "name": "Beach relaxation", ... }
            }
          ]
        }
      }
    },
    {
      "type": "swap_days",
      "day_a": 4,
      "day_b": 5
    }
  ]
}
```

### Change Types

| Type | Description | Fields |
|------|-------------|--------|
| `add_day` | Insert a new day | `position`, `day` |
| `remove_day` | Remove an existing day | `day_number` |
| `modify_day` | Change day properties/activities | `day_number`, `changes` |
| `swap_days` | Exchange two days | `day_a`, `day_b` |
| `modify_metadata` | Change title, dates, tips, etc. | `field`, `old_value`, `new_value` |

### File Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `models/itinerary.py` | Modify | Add diff-related models |
| `agents/base.py` | Modify | Add `ITINERARY_UPDATE_PROMPT` and `generate_itinerary_update()` |
| `agents/claude_agent.py` | Modify | Implement `generate_itinerary_update()` |
| `agents/openai_agent.py` | Modify | Implement `generate_itinerary_update()` |
| `agents/gemini_agent.py` | Modify | Implement `generate_itinerary_update()` |
| `services/itinerary_updater.py` | Create | Diff application and preview logic |
| `app.py` | Modify | Add diff UI components to Itinerary tab |

## Out of Scope

- Undo/redo functionality (future enhancement)
- Collaborative editing with conflict resolution
- Version history persistence beyond current session
- Automatic change suggestions

## Success Metrics

1. **Token Reduction**: 60%+ reduction in tokens for typical single-day updates
2. **User Satisfaction**: Users can successfully apply 90%+ of requested changes without full regeneration
3. **Accuracy**: Less than 5% of updates contain unintended side effects

## Dependencies

- Existing itinerary generation infrastructure
- All three AI providers must support the update prompt format
- Streamlit session state for tracking pending changes
