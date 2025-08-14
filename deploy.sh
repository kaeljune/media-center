#!/bin/bash

# Deploy script cho Media Center

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ACTION="up"
BUILD=false
LOGS=false

usage() {
    echo "Usage: $0 [OPTIONS] [ACTION]"
    echo ""
    echo "Actions:"
    echo "  up        Start services (default)"
    echo "  down      Stop services"
    echo "  restart   Restart services"
    echo "  logs      Show logs"
    echo "  status    Show status"
    echo ""
    echo "Options:"
    echo "  --build   Build images before starting"
    echo "  --logs    Follow logs after starting"
    echo "  -h, --help Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start services"
    echo "  $0 --build up        # Build and start"
    echo "  $0 down              # Stop services"
    echo "  $0 logs              # Show logs"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD=true
            shift
            ;;
        --logs)
            LOGS=true
            shift
            ;;
        up|down|restart|logs|status)
            ACTION="$1"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

# Detect OS and use appropriate compose file
COMPOSE_FILE="docker-compose.yml"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    COMPOSE_FILE="docker-compose.linux.yml"
    echo -e "${YELLOW}Using Linux compose file for audio device access${NC}"
fi

echo -e "${BLUE}Media Center Deployment${NC}"
echo "Action: $ACTION"
echo ""

case $ACTION in
    up)
        if [ "$BUILD" = true ]; then
            echo -e "${YELLOW}Building images...${NC}"
            docker-compose -f "$COMPOSE_FILE" build
        fi
        
        echo -e "${YELLOW}Starting services...${NC}"
        docker-compose -f "$COMPOSE_FILE" up -d
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Services started successfully!${NC}"
            echo ""
            echo -e "${YELLOW}Service URLs:${NC}"
            echo "  Health Check: http://localhost:8000/health"
            echo "  TTS API:     http://localhost:8000/tts"
            echo "  HC3 API:     http://localhost:8000/hc3/command"
            echo "  Status:      http://localhost:8000/status"
            echo ""
            echo -e "${YELLOW}Test commands:${NC}"
            echo "  curl http://localhost:8000/health"
            echo "  curl -X POST http://localhost:8000/tts -H 'Content-Type: application/json' -d '{\"text\":\"Hello World\"}'"
            
            if [ "$LOGS" = true ]; then
                echo ""
                echo -e "${YELLOW}Following logs...${NC}"
                docker-compose -f "$COMPOSE_FILE" logs -f
            fi
        else
            echo -e "${RED}✗ Failed to start services!${NC}"
            exit 1
        fi
        ;;
        
    down)
        echo -e "${YELLOW}Stopping services...${NC}"
        docker-compose -f "$COMPOSE_FILE" down
        echo -e "${GREEN}✓ Services stopped${NC}"
        ;;
        
    restart)
        echo -e "${YELLOW}Restarting services...${NC}"
        docker-compose -f "$COMPOSE_FILE" restart
        echo -e "${GREEN}✓ Services restarted${NC}"
        ;;
        
    logs)
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
        
    status)
        echo -e "${YELLOW}Service Status:${NC}"
        docker-compose -f "$COMPOSE_FILE" ps
        echo ""
        
        # Check if services are responding
        if curl -s http://localhost:8000/health > /dev/null; then
            echo -e "${GREEN}✓ API is responding${NC}"
        else
            echo -e "${RED}✗ API is not responding${NC}"
        fi
        ;;
        
    *)
        echo -e "${RED}Unknown action: $ACTION${NC}"
        usage
        exit 1
        ;;
esac