from tree_sitter_languages import get_parser
 
def chunk_tree(code_string: str, language: str, file_name: str = "unknown"):
    parser = get_parser(language)
    tree = parser.parse(bytes(code_string, "utf8"))

    root = tree.root_node
    chunks = []

    SKIP_TYPES = {
        "comment", "newline", "", "module",
        "import_statement", "import_from_statement",
        "import_declaration", "preproc_include",
    }

    # only chunk these meaningful top-level types
    CHUNK_TYPES = {
        "function_definition",      # Python functions
        "class_definition",         # Python classes
        "method_declaration",       # Java methods
        "class_declaration",        # Java classes
        "function_declarator",      # C++ functions
        "struct_specifier",         # C++ structs
        "decorated_definition",     # Python decorators + function/class
    }

    for node in root.children:
        if node.type in SKIP_TYPES:
            continue

        if node.type in CHUNK_TYPES:
            name_node = node.child_by_field_name("name")
            name = code_string[name_node.start_byte:name_node.end_byte] if name_node else node.type
            chunk_text = code_string[node.start_byte:node.end_byte]

            chunks.append({
                "file":       file_name,
                "node_type":  node.type,
                "name":       name,
                'Source_type': 'Documents',
                "text":       chunk_text,
                "start_line": node.start_point[0] + 1,
                "end_line":   node.end_point[0] + 1,
            })

        # anything else at top level (assignments, expressions) — group together
        else:
            chunk_text = code_string[node.start_byte:node.end_byte].strip()
            if len(chunk_text) > 30:   # skip trivial one-liners
                chunks.append({
                    "file":       file_name,
                    "node_type":  node.type,
                    "name":       node.type,
                    'Source_type': 'Documents',
                    "text":       chunk_text,
                    "start_line": node.start_point[0] + 1,
                    "end_line":   node.end_point[0] + 1,
                })

    return chunks