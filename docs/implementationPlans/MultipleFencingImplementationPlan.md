# Multiple Fencing Feature Implementation Plan

## 1. Objective

### Scope
- Multiple named fence blocks within prompts
- Each fence has: name, format, content, and position
- Supported formats: brackets, triple quotes, XML tags, markdown
- Drag-and-drop reordering using SortableJS
- Vanilla JavaScript implementation (no frameworks)

### Technical Boundaries
- No nested fence support initially
- Single-file editor approach
- Format is immutable after fence creation
- Basic validation: non-null name, non-empty content

## 2. Business Value
- Structured organization of prompt components
- Mix-and-match different fence formats in one prompt
- Intuitive reordering through drag-and-drop
- Clear visual separation of prompt sections
- Backward compatibility with existing prompts

## 3. Implementation Steps

### Step 1: Database Schema
**Description**: Create Fence model and update Prompt model relationships

**Manual Testing**:
1. Open database viewer (e.g., SQLite Browser)
2. Verify fence table with columns: id, prompt_id, name, format, content, position
3. Check foreign key constraint between prompt and fence tables

**Acceptance Criteria**:
- [ ] Fence table exists with all required columns
- [ ] Foreign key constraint enforces prompt-fence relationship
- [ ] Position column allows reordering

**Commit**: "feat(db): Add Fence model and prompt relationships"

### Step 2: Data Migration
**Description**: Convert existing prompts to use fence structure

**Manual Testing**:
1. Open any existing prompt in the editor
2. Verify content appears in a default fence
3. Check prompt still renders correctly

**Acceptance Criteria**:
- [ ] All existing prompts accessible
- [ ] No content loss during migration
- [ ] Legacy format compatibility maintained

**Commit**: "feat(db): Migrate existing prompts to fence structure"

### Step 3: Backend API
**Description**: Add fence management endpoints

**Manual Testing**:
1. Use Postman/curl to:
   - Create new fence (POST /prompts/{id}/fences)
   - Update fence order (PUT /prompts/{id}/fences/reorder)
   - Delete fence (DELETE /prompts/{id}/fences/{fence_id})
2. Verify responses and database state

**Acceptance Criteria**:
- [ ] All CRUD operations work
- [ ] Order updates persist correctly
- [ ] Proper error handling for invalid requests

**Commit**: "feat(api): Add fence management endpoints"

### Step 4: Frontend Base
**Description**: Create fence editor UI components

**Manual Testing**:
1. Open prompt editor
2. Verify fence list display
3. Test fence creation form
4. Check format selector options

**Acceptance Criteria**:
- [ ] Fences visually distinct
- [ ] Format selector shows all options
- [ ] New fence form works

**Commit**: "feat(ui): Add fence editor components"

### Step 5: Drag-Drop
**Description**: Implement fence reordering

**Manual Testing**:
1. Drag fence up/down
2. Check order persists after page reload
3. Verify visual feedback during drag

**Acceptance Criteria**:
- [ ] Smooth drag animation
- [ ] Order updates in backend
- [ ] Visual feedback during drag

**Commit**: "feat(ui): Add fence reordering"

### Step 6: Format Handling
**Description**: Implement format-specific rendering

**Manual Testing**:
1. Create fences with different formats
2. Verify correct rendering of each format
3. Check format persistence after edits

**Acceptance Criteria**:
- [ ] All formats render correctly
- [ ] Format remains fixed after creation
- [ ] No interference between formats

**Commit**: "feat(core): Add format-specific rendering"

## 4. Main Challenges

### Concurrent Editing
**Problem**: Multiple users editing same prompt
**Solution**: 
- Transaction-based order updates
- Optimistic locking for content changes
- Clear error messages on conflicts

### Format Parsing
**Problem**: Different formats in same prompt
**Solution**:
- Clear format boundaries
- Format-specific parsers
- Strict validation rules

### Order Management
**Problem**: Maintaining consistent order
**Solution**:
- Database-level position tracking
- Batch updates for reordering
- Position normalization after deletes

## 5. Abstractions

### FenceManager (Used in Steps 3, 4)
```python
class FenceManager:
    def create_fence(self, prompt_id, data)
    def update_order(self, prompt_id, positions)
    def delete_fence(self, fence_id)
```
Purpose: Central fence operations handler

### FenceRenderer (Used in Step 6)
```python
class FenceRenderer:
    def render(self, fence)
    def get_format_rules(self, format_type)
```
Purpose: Format-specific rendering logic

### Integration Points
1. **PromptHandler Extension** (Step 3)
   - Add fence management methods
   - Update prompt compilation

2. **Editor Integration** (Steps 4, 5)
   - Fence list component
   - SortableJS initialization
   - Format selector

3. **Database Layer** (Steps 1, 2)
   - Model relationships
   - Migration handlers
   - Order management
