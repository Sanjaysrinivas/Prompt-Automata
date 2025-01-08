# Dynamic Reference System Implementation Plan

## 1. Objective

Implement a dynamic fencing system that supports multiple reference types within the same fence, with:
- Restricted file path references (relative paths within allowed directories)
- Persistent variables (SQLite-stored)
- Generic REST API references (with GitHub as initial implementation)

Technical Boundaries:
- References resolved at input time with async validation
- SQLite for persistent variable and allowed directory storage
- Generic REST API handler with GitHub implementation
- Extended @[type:value] syntax for all reference types
- File paths restricted to predefined target directories

## 2. Business Value

- Enhanced Modularity: References can be dynamically updated without modifying fence content
- Improved Reusability: Global persistent variables accessible across prompts
- Flexible Integration: Generic REST API handler enables easy addition of new API integrations
- Structured Data Management: Consistent SQLite-based storage for variables and configurations
- Enhanced Security: Restricted file access through predefined target directories

## 3. Implementation Steps

### Step 1: Database Schema Enhancement
**Description**: Add models for persistent variables, allowed directories, and reference tracking

**Tasks**:
1. Create PersistentVariable model
2. Create AllowedDirectory model for file path restrictions
3. Create FenceReference model
4. Create APIEndpoint model for storing API configurations
5. Update Fence model with reference fields
6. Create database migrations

**Manual Testing**:
1. Create a new persistent variable via admin interface
2. Add allowed directory and verify path validation
3. Configure API endpoint and verify storage
4. Create a fence with references and check database entries

**Commit**: "feat(db): Add reference system models and directory restrictions"

**Acceptance Criteria**:
- [ ] All models created with correct relationships
- [ ] Migrations run successfully
- [ ] Admin interface shows new models
- [ ] Basic CRUD operations work for all models
- [ ] Directory paths properly validated

### Step 2: Core Abstractions
**Description**: Implement core abstractions for reference handling

**Tasks**:
1. Create ReferenceHandler base interface
2. Create APIHandler base class with:
   - Endpoint configuration
   - Authentication handling
   - Response parsing interface
3. Create FilePathValidator for directory restrictions
4. Create ReferenceManager

**Manual Testing**:
1. Configure and test API endpoint connection
2. Validate file paths against allowed directories
3. Test authentication handling
4. Verify error handling for invalid configurations

**Commit**: "feat(core): Add reference handling abstractions"

**Acceptance Criteria**:
- [ ] API handler successfully manages endpoints
- [ ] File paths properly restricted
- [ ] Authentication works for API endpoints
- [ ] Error handling implemented for all cases

### Step 3: Reference Implementations
**Description**: Implement specific reference handlers

**Tasks**:
1. Implement RestrictedFileHandler with directory validation
2. Implement VariableReferenceHandler
3. Implement GitHubAPIHandler extending APIHandler
4. Create reference resolution pipeline

**Manual Testing**:
1. Test file reference within allowed directory
2. Verify rejection of file paths outside allowed directories
3. Test GitHub API integration
4. Verify variable resolution

**Commit**: "feat(handlers): Add reference type implementations"

**Acceptance Criteria**:
- [ ] File paths restricted to allowed directories
- [ ] GitHub integration works through generic API handler
- [ ] Variables resolve correctly
- [ ] Invalid references return appropriate errors

### Step 4: Frontend Components
**Description**: Create UI components with enhanced validation

**Tasks**:
1. Create reference input component with path validation
2. Create API configuration interface
3. Create reference preview component
4. Update fence block template
5. Add directory management interface (optional)

**Manual Testing**:
1. Enter file reference and verify directory restriction
2. Configure and test API endpoint
3. Preview resolved references
4. Test error handling and validation feedback

**Commit**: "feat(ui): Add reference components with validation"

**Acceptance Criteria**:
- [ ] Path validation works in UI
- [ ] API configuration interface functional
- [ ] Preview shows resolved content
- [ ] Clear error feedback for invalid paths

## 4. Main Challenges

1. **API Integration Flexibility**
   - Solution: Generic APIHandler abstraction
   - Configurable endpoint and response mapping
   - Extensible authentication methods

2. **File Path Security**
   - Solution: AllowedDirectory model with path validation
   - Relative path resolution within allowed directories
   - Path traversal prevention

3. **Reference Resolution Performance**
   - Solution: Async resolution with caching
   - Parallel resolution for multiple references
   - Cached API responses

4. **Multiple Reference Types**
   - Solution: Unified resolution pipeline
   - Type-specific validation and resolution
   - Consistent error handling

## 5. Abstractions

### Core Abstractions
1. **ReferenceHandler Interface**
   - Base interface for all reference types
   - Integration: Step 2 - Core Abstractions

2. **APIHandler Abstract Class**
   - Generic REST API integration
   - Endpoint configuration
   - Response parsing
   - Authentication management
   - Integration: Step 2 - Core Abstractions

3. **FilePathValidator**
   - Directory restriction logic
   - Path validation and resolution
   - Integration: Step 2 - Core Abstractions

### Implementations
1. **GitHubAPIHandler**
   - Extends APIHandler
   - GitHub-specific endpoint mapping
   - Integration: Step 3 - Reference Implementations

2. **RestrictedFileHandler**
   - Uses FilePathValidator
   - Handles relative path resolution
   - Integration: Step 3 - Reference Implementations

### Architecture Integration
1. **Database Models**
   - AllowedDirectory for path restrictions
   - APIEndpoint for API configurations
   - Integration: Step 1 - Database Schema

2. **Reference Resolution Pipeline**
   - Unified handling of all reference types
   - Integration: Step 3 - Reference Implementations

3. **UI Components**
   - Path validation feedback
   - API configuration interface
   - Integration: Step 4 - Frontend Components
