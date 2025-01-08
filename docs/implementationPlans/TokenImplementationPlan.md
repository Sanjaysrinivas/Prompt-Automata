# Token Counting Implementation Plan

## 1. Objective

Implement a robust token counting system using Tiktoken that provides:
- Accurate token counting for both raw content and resolved references
- Support for all reference types (files, API endpoints, variables)
- Performance optimization through hierarchical caching
- Real-time UI feedback with warning thresholds
- Efficient handling of large token counts

Technical Boundaries:
- Tiktoken cl100k_base encoding for consistent counting
- Hierarchical caching (memory → DB)
- Background processing for non-critical counts
- Streaming support for large files
- Reference-specific caching strategies

## 2. Business Value

- Improved Prompt Management: Accurate tracking of token usage across all content
- Enhanced User Experience: Real-time feedback during content creation
- Cost Optimization: Proactive management of token limits
- Better Debugging: Clear visibility into token usage patterns
- Performance Optimization: Efficient handling of large content through caching

## 3. Implementation Steps

### Step 1: Core Token Counting Service
**Description**: Implement base token counting service with caching

**Tasks**:
1. Create TokenCountingService with cl100k_base encoding
2. Implement error handling with retries and custom exceptions
3. Add in-memory LRU cache with invalidation strategy
4. Create TokenCount SQLAlchemy model for persistent storage
5. Implement hierarchical cache (memory → DB) with hit/miss logging

**Manual Testing**:
1. Count tokens in basic strings, verify against tiktoken output
2. Trigger errors, verify graceful handling and retries
3. Test cache hits and misses
4. Verify cache persistence across service restarts

**Commit**: "feat: Implement TokenCountingService with caching"

**Acceptance Criteria**:
- [ ] Token counting matches tiktoken output
- [ ] Error handling works with proper retries
- [ ] Cache hierarchy functions correctly
- [ ] Persistence works across restarts

### Step 2: Reference Type Handlers
**Description**: Implement reference-specific token counting

**Tasks**:
1. Create streaming file content handler with hash-based caching
2. Implement API response handler with retry logic and pattern caching
3. Add variable content handler with change detection
4. Create batch processing for multiple references

**Manual Testing**:
1. Count tokens in large files (>1MB)
2. Test API response caching
3. Verify variable change detection
4. Test batch processing performance

**Commit**: "feat: Add reference type handlers with caching"

**Acceptance Criteria**:
- [ ] Large files processed efficiently
- [ ] API responses cached correctly
- [ ] Variable changes trigger recounts
- [ ] Batch processing improves performance

### Step 3: Background Processing
**Description**: Implement background processing system

**Tasks**:
1. Create background worker queue with priority levels
2. Implement task status tracking and monitoring
3. Add batch processing optimization
4. Create error recovery mechanism with backoff

**Manual Testing**:
1. Queue multiple tasks with different priorities
2. Monitor task processing order
3. Test error recovery scenarios
4. Verify batch processing efficiency

**Commit**: "feat: Implement background processing system"

**Acceptance Criteria**:
- [ ] Tasks process in correct priority order
- [ ] System recovers from errors gracefully
- [ ] Background processing doesn't block UI
- [ ] Batch processing works efficiently

### Step 4: UI Integration
**Description**: Implement UI components for token counting

**Tasks**:
1. Create token count display with loading states
2. Add debounced real-time updates
3. Implement warning system with thresholds
4. Add reference resolution indicators

**Manual Testing**:
1. Type rapidly and verify update smoothness
2. Test warning threshold triggers
3. Verify loading state visibility
4. Check reference resolution feedback

**Commit**: "feat: Add token counting UI integration"

**Acceptance Criteria**:
- [ ] Updates are smooth during typing
- [ ] Warnings appear at correct thresholds
- [ ] Loading states are clear
- [ ] Reference resolution status is visible

## 4. Main Challenges

1. **Performance Management**
   - Solution: Hierarchical caching strategy
   - Background processing with prioritization
   - Streaming for large files

2. **Error Handling**
   - Solution: Typed exceptions with retry logic
   - Graceful degradation with feedback
   - Background task recovery

3. **UI Responsiveness**
   - Solution: Debounced updates
   - Progressive loading feedback
   - Clear visual indicators

## 5. Abstractions

### Core Components
1. **TokenCountingService**
   - Token counting logic
   - Error handling
   - Cache management

2. **ReferenceHandlers**
   - Type-specific processing
   - Caching strategies
   - Change detection

3. **BackgroundProcessor**
   - Task queue management
   - Priority handling
   - Error recovery

4. **UIComponents**
   - Display management
   - Update handling
   - Warning system
