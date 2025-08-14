#!/bin/bash

# Build script cho Media Center Docker container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="mediacenter"
TAG="latest"
PLATFORM=""
PUSH=false

# Print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -n, --name NAME       Image name (default: mediacenter)"
    echo "  -t, --tag TAG         Image tag (default: latest)"
    echo "  -p, --platform PLATFORM  Target platform (amd64, arm64, linux/arm64)"
    echo "  --push                Push to registry after build"
    echo "  -h, --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Build for current platform"
    echo "  $0 -p linux/arm64                   # Build for Jetson Nano (ARM64)"
    echo "  $0 -p linux/amd64                   # Build for x86_64 (macOS/Linux)"
    echo "  $0 -n myregistry/mediacenter --push # Build and push to registry"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        --push)
            PUSH=true
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

# Detect platform if not specified
if [ -z "$PLATFORM" ]; then
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            PLATFORM="linux/amd64"
            ;;
        aarch64|arm64)
            PLATFORM="linux/arm64"
            ;;
        *)
            echo -e "${RED}Unsupported architecture: $ARCH${NC}"
            exit 1
            ;;
    esac
fi

FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

echo -e "${GREEN}Building Media Center Docker image...${NC}"
echo "Image: $FULL_IMAGE_NAME"
echo "Platform: $PLATFORM"
echo ""

# Build the image
echo -e "${YELLOW}Building Docker image...${NC}"
if [ "$PLATFORM" != "" ]; then
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$FULL_IMAGE_NAME" \
        --load \
        .
else
    docker build -t "$FULL_IMAGE_NAME" .
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build completed successfully!${NC}"
else
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi

# Push if requested
if [ "$PUSH" = true ]; then
    echo -e "${YELLOW}Pushing to registry...${NC}"
    docker push "$FULL_IMAGE_NAME"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Push completed successfully!${NC}"
    else
        echo -e "${RED}✗ Push failed!${NC}"
        exit 1
    fi
fi

# Show image info
echo ""
echo -e "${GREEN}Image built successfully:${NC}"
docker images | grep "$IMAGE_NAME" | head -1

echo ""
echo -e "${YELLOW}To run the container:${NC}"
echo "docker-compose up -d"
echo ""
echo -e "${YELLOW}Or manually:${NC}"
echo "docker run -d -p 8000:8000 -p 8001:8001 --name mediacenter $FULL_IMAGE_NAME"