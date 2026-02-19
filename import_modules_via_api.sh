#!/bin/bash
# Import MI Learning Modules to Supabase via REST API
# This script doesn't require Python dependencies - uses curl
# 
# USAGE: Set environment variables before running:
#   export SUPABASE_URL="https://your-project.supabase.co"
#   export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
#   ./import_modules_via_api.sh

set -e

# Supabase credentials from environment
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set as environment variables"
    echo "Example:"
    echo "  export SUPABASE_URL='https://your-project.supabase.co'"
    echo "  export SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'"
    exit 1
fi

echo "============================================================"
echo "MI Learning Platform - Module Import via REST API"
echo "============================================================"
echo "Supabase URL: $SUPABASE_URL"
echo ""

# Function to import a single module
import_module() {
    local module_number=$1
    local json_file=$2

    echo "------------------------------------------------------------"
    echo "Importing Module $module_number from $json_file"
    echo "------------------------------------------------------------"

    # Read JSON content
    local json_content=$(cat "$json_file")

    # Extract using jq or Python (fallback to basic string manipulation)
    # We'll use the Supabase REST API to insert the data

    # Create the module record
    local endpoint="${SUPABASE_URL}/rest/v1/learning_modules"

    # Build the JSON payload
    local title=$(echo "$json_content" | grep -o '"title": "[^"]*"' | head -1 | cut -d'"' -f4)
    local learning_objective=$(echo "$json_content" | grep -o '"learning_objective": "[^"]*"' | head -1 | cut -d'"' -f4)
    local technique_focus=$(echo "$json_content" | grep -o '"technique_focus": "[^"]*"' | head -1 | cut -d'"' -f4)
    local stage_of_change=$(echo "$json_content" | grep -o '"stage_of_change": "[^"]*"' | head -1 | cut -d'"' -f4)
    local description=$(echo "$json_content" | grep -o '"description": "[^"]*"' | head -1 | cut -d'"' -f4)

    # Create slug from title
    local slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')

    # Build the JSON payload for the module
    # NOTE: max_points_available is calculated by calling the recalculate endpoint after import
    local payload=$(cat <<EOF
{
  "module_number": $module_number,
  "title": "$title",
  "slug": "$slug",
  "learning_objective": "$learning_objective",
  "technique_focus": "$technique_focus",
  "stage_of_change": "$stage_of_change",
  "description": "$description",
  "dialogue_content": $(echo "$json_content" | sed 's/"/\\"/g'),
  "is_published": true,
  "display_order": $module_number
}
EOF
)

    # Check if module already exists
    local check_response=$(curl -s "${endpoint}?module_number=eq.${module_number}&select=id" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}")

    if echo "$check_response" | grep -q '"id"'; then
        echo "  Module already exists, updating..."
        local module_id=$(echo "$check_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
        curl -s "${endpoint}?id=eq.${module_id}" \
            -X PATCH \
            -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
            -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
            -H "Content-Type: application/json" \
            -d "$payload"
    else
        echo "  Inserting new module..."
        curl -s "${endpoint}" \
            -X POST \
            -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
            -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
            -H "Content-Type: application/json" \
            -d "$payload"
    fi

    echo "  ✓ Module $module_number imported"
}

# Main import logic
main() {
    local modules_dir="mi_modules"

    if [ ! -d "$modules_dir" ]; then
        echo "ERROR: mi_modules directory not found"
        exit 1
    fi

    echo "Found modules in: $modules_dir"
    echo ""

    # Import modules 1-12
    local success_count=0
    for i in {1..12}; do
        local json_file="${modules_dir}/module_${i}.json"
        if [ -f "$json_file" ]; then
            if import_module "$i" "$json_file"; then
                ((success_count++))
            fi
        else
            echo "⚠ Module $i file not found: $json_file"
        fi
    done

    echo ""
    echo "============================================================"
    echo "Import complete: $success_count/12 modules"
    echo "============================================================"
    echo ""
    echo "IMPORTANT: After import, recalculate max_points_available by calling:"
    echo "  curl -X POST \"\${SUPABASE_URL}/api/v1/admin/modules/recalculate-points\" \\"
    echo "    -H \"Authorization: Bearer \$ADMIN_TOKEN\""
    echo ""
    echo "Or use the admin dashboard to recalculate points."
}

# Run main
main "$@"
