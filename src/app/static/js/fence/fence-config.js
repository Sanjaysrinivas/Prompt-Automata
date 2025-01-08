// Configuration settings for fence editor

export const EDITOR_OPTIONS = {
    mode: 'markdown',
    theme: 'default',
    lineNumbers: true,
    lineWrapping: true,
    autoCloseBrackets: true,
    matchBrackets: true,
    indentUnit: 4,
    tabSize: 4,
    scrollbarStyle: 'native',
    viewportMargin: Infinity,
    extraKeys: {
        'Tab': 'indentMore',
        'Shift-Tab': 'indentLess',
        'Ctrl-Space': 'autocomplete'
    }
};

export const FENCE_FORMATS = {
    xml_tags: {
        name: 'XML Tags',
        description: 'Wraps content in XML-style tags'
    },
    triple_quotes: {
        name: 'Triple Quotes',
        description: 'Wraps content in triple quotes'
    },
    curly_braces: {
        name: 'Curly Braces',
        description: 'Wraps content in curly braces'
    },
    markdown: {
        name: 'Markdown',
        description: 'Wraps content in markdown code block'
    }
};

export const API_ENDPOINTS = {
    countTokens: '/api/count_text',
    saveBlock: '/api/save_block',
    loadBlock: '/api/load_block',
    getReferenceOptions: '/api/reference-options',
    refreshBlock: '/api/refresh/block',
    refreshAll: '/api/refresh/all'
};
