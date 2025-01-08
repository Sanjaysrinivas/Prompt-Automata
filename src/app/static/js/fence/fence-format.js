// Utility functions for formatting fence content

export function wrapContentInFormat(content, format, name = '') {
    if (!content) return '';
    name = name.trim() || 'fence';  // Default to 'fence' if no name provided and trim whitespace
    
    // Check if it's an XML type fence (if the name contains any XML-like tags or format is explicitly xml_tags)
    const isXmlType = format === 'xml_tags' || name.includes('<') || name.includes('>');
    
    if (isXmlType) {
        // For XML type, always wrap in XML tags
        const cleanName = name.replace(/[<>/]/g, '').trim(); // Remove any existing XML symbols
        return `<${cleanName}>\n${content}\n</${cleanName}>`;
    }
    
    // For non-XML types, use the specified format
    switch (format) {
        case 'triple_quotes':
            return `${name}\n"""\n${content}\n"""`;
        case 'markdown':
            return `${name}\n\`\`\`\n${content}\n\`\`\``;
        case 'curly_braces':
            return `${name}\n{\n${content}\n}`;
        default:
            // Default to triple backticks if no specific format is specified
            return `${name}\n\`\`\`\n${content}\n\`\`\``;
    }
}
