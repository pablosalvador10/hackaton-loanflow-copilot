#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  Toggle Cosmos DB public access for local development
#
#  Usage:
#    ./scripts/cosmos-public-access.sh open    # Enable public access (your IP only)
#    ./scripts/cosmos-public-access.sh close   # Disable public access
#    ./scripts/cosmos-public-access.sh status  # Show current state
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

COSMOS_ACCOUNT="cosmos-router-chat-81d5ff"
RESOURCE_GROUP="router-chat-rg"

# ── Helpers ──────────────────────────────────────────────────────

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$*"; }

get_my_ip() {
    # Force IPv4 — Cosmos DB IP rules don't support IPv6
    curl -4 -s --max-time 5 ifconfig.me || curl -4 -s --max-time 5 api.ipify.org || {
        red "ERROR: Could not determine your public IPv4 address"
        exit 1
    }
}

show_status() {
    echo "Checking Cosmos DB: $COSMOS_ACCOUNT ..."
    az cosmosdb show \
        --name "$COSMOS_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --query "{publicAccess:publicNetworkAccess, ipRules:ipRangeFilter}" \
        -o json
}

# ── Commands ─────────────────────────────────────────────────────

cmd_open() {
    MY_IP=$(get_my_ip)
    echo ""
    yellow "Opening Cosmos DB public access for IP: $MY_IP"
    echo "  Account: $COSMOS_ACCOUNT"
    echo "  Resource Group: $RESOURCE_GROUP"
    echo ""

    az cosmosdb update \
        --name "$COSMOS_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --public-network-access ENABLED \
        --ip-range-filter "$MY_IP" \
        --output none

    green "✓ Public access ENABLED (restricted to $MY_IP)"
    echo ""
    echo "You can now connect from your laptop."
    echo "Run './scripts/cosmos-public-access.sh close' when done."
}

cmd_close() {
    echo ""
    yellow "Closing Cosmos DB public access..."
    echo "  Account: $COSMOS_ACCOUNT"
    echo "  Resource Group: $RESOURCE_GROUP"
    echo ""

    az cosmosdb update \
        --name "$COSMOS_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --public-network-access DISABLED \
        --ip-range-filter "" \
        --output none

    green "✓ Public access DISABLED"
    echo "  Cosmos DB is now only reachable via private endpoint (VNet)."
}

cmd_status() {
    show_status
}

# ── Main ─────────────────────────────────────────────────────────

case "${1:-}" in
    open)   cmd_open   ;;
    close)  cmd_close  ;;
    status) cmd_status ;;
    *)
        echo "Usage: $0 {open|close|status}"
        echo ""
        echo "  open    Enable public access restricted to your current IP"
        echo "  close   Disable public access (private endpoint only)"
        echo "  status  Show current public access state"
        exit 1
        ;;
esac
