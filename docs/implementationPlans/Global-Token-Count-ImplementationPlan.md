# Token Counting 2.0 Implementation Plan

## 1. Objective

Implement an enhanced token counting system that provides:
- Global token counting across all fence blocks
- Real-time synchronous token calculation
- Floating status indicator with model capacity visualization
- Reference and file token inclusion

Technical Boundaries:
- Synchronous token counting for immediate feedback
- Floating dialog UI using existing modal system
- Model-specific token limits (200K, 128K, 32K)
- Reference and file token inclusion

## 2. Business Value

- Enhanced User Experience: Real-time global token feedback
- Improved Visibility: Clear visualization of token usage across models
- Efficient Token Management: Immediate feedback on token usage
- Streamlined Editing: Real-time token count updates

## 3. Implementation Steps

### Step 1: Global Token Counter Module
**Description**: Create core global token counting functionality

**Tasks**:
1. Create GlobalTokenCounter class with event system
2. Implement synchronous token counting wrapper
3. Add block registration and tracking system
4. Create token aggregation logic across blocks
5. Implement change detection and recalculation

**Manual Testing**:
1. Register multiple blocks and verify total
2. Test synchronous counting accuracy
3. Verify change detection triggers
4. Test performance with many blocks

**Commit**: "feat: Implement GlobalTokenCounter with sync counting"

**Acceptance Criteria**:
- [ ] Accurate global token counting
- [ ] Synchronous updates work reliably
- [ ] Change detection functions correctly
- [ ] Performance remains good with multiple blocks

### Step 2: Floating Dialog UI
**Description**: Implement persistent token status indicator

**Tasks**:
1. Create floating dialog component using existing modal system
2. Implement model capacity visualization
3. Create block size breakdown view
4. Add smooth UI updates

**Manual Testing**:
1. Verify dialog positioning and persistence
2. Test model capacity bar accuracy
3. Verify UI responsiveness
4. Test with multiple blocks

**Commit**: "feat: Add floating token status dialog"

**Acceptance Criteria**:
- [ ] Dialog displays correctly and persists
- [ ] Model capacities show accurately
- [ ] UI remains responsive
- [ ] Updates are smooth and efficient

### Step 3: Reference Token Integration
**Description**: Implement comprehensive token counting

**Tasks**:
1. Create reference token counting system
2. Implement file reference handling
3. Add API reference resolution
4. Create variable reference handling

**Manual Testing**:
1. Test with various reference types
2. Verify file reference counting
3. Check API reference resolution
4. Test variable reference updates

**Commit**: "feat: Add reference token counting"

**Acceptance Criteria**:
- [ ] All reference types counted correctly
- [ ] File references handled efficiently
- [ ] API references resolve properly
- [ ] Variable references update correctly

### Step 4: Integration and Optimization
**Description**: Integrate with existing systems and optimize

**Tasks**:
1. Connect with existing fence block system
2. Implement performance optimizations
3. Add caching mechanisms
4. Create error recovery system

**Manual Testing**:
1. Test with existing fence blocks
2. Verify system performance
3. Check cache effectiveness
4. Test error handling

**Commit**: "feat: Complete token counting integration"

**Acceptance Criteria**:
- [ ] Seamless integration with fence blocks
- [ ] System performs efficiently
- [ ] Caching works effectively
- [ ] Errors handled gracefully

## 4. Main Challenges

1. **Synchronous Performance**
   - Solution: Efficient token counting implementation
   - Optimized change detection
   - Smart recalculation triggers

2. **UI Responsiveness**
   - Solution: Lightweight floating dialog
   - Efficient DOM updates
   - Smooth visualization updates

3. **Reference Resolution**
   - Solution: Efficient reference handling
   - Smart caching strategy
   - Quick token recalculation

## 5. Abstractions

### Core Components
1. **GlobalTokenCounter**
   - Token counting logic
   - Block management
   - Event system

2. **FloatingDialog**
   - Status display
   - Model visualization
   - Real-time updates

3. **ReferenceHandler**
   - Reference resolution
   - Token calculation
   - Cache management

4. **TokenCalculator**
   - Synchronous counting
   - Reference resolution
   - Cache optimization
