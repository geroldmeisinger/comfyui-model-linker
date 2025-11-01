"""
@author: Model Linker Team
@title: ComfyUI Model Linker
@nickname: Model Linker
@version: 1.0.0
@description: Extension for relinking missing models in ComfyUI workflows using fuzzy matching
"""

import logging

# Web directory for JavaScript interface
WEB_DIRECTORY = "./web"

# Empty NODE_CLASS_MAPPINGS - we don't provide custom nodes, only web extension
# This prevents ComfyUI from showing "IMPORT FAILED" message
NODE_CLASS_MAPPINGS = {}

__all__ = ["WEB_DIRECTORY"]


class ModelLinkerExtension:
    """Main extension class for Model Linker."""
    
    def __init__(self):
        self.routes_setup = False
        self.logger = logging.getLogger(__name__)
    
    def initialize(self):
        """Initialize the extension and set up API routes."""
        try:
            self.setup_routes()
            self.logger.info("Model Linker: Extension initialized successfully")
        except Exception as e:
            self.logger.error(f"Model Linker: Extension initialization failed: {e}", exc_info=True)
    
    def setup_routes(self):
        """Register API routes for the Model Linker extension."""
        if self.routes_setup:
            return  # Already set up
        
        try:
            from aiohttp import web
            
            # Try to get routes from PromptServer
            try:
                from server import PromptServer
                if not hasattr(PromptServer, 'instance') or PromptServer.instance is None:
                    self.logger.debug("Model Linker: PromptServer not available yet")
                    return False
                
                routes = PromptServer.instance.routes
            except (ImportError, AttributeError) as e:
                self.logger.debug(f"Model Linker: Could not access PromptServer: {e}")
                return False
            
            # Import linker modules - use relative imports which should work for packages
            try:
                from .core.linker import analyze_and_find_matches, apply_resolution
                from .core.scanner import get_model_files
            except ImportError as e:
                self.logger.error(f"Model Linker: Could not import core modules: {e}")
                return False
            
            @routes.post("/model_linker/analyze")
            async def analyze_workflow(request):
                """Analyze workflow and return missing models with matches."""
                try:
                    data = await request.json()
                    workflow_json = data.get('workflow')
                    
                    if not workflow_json:
                        return web.json_response(
                            {'error': 'Workflow JSON is required'},
                            status=400
                        )
                    
                    # Analyze and find matches
                    result = analyze_and_find_matches(workflow_json)
                    
                    return web.json_response(result)
                except Exception as e:
                    self.logger.error(f"Model Linker analyze error: {e}", exc_info=True)
                    return web.json_response(
                        {'error': str(e)},
                        status=500
                    )
            
            @routes.post("/model_linker/resolve")
            async def resolve_models(request):
                """Apply model resolution and return updated workflow."""
                try:
                    data = await request.json()
                    workflow_json = data.get('workflow')
                    resolutions = data.get('resolutions', [])
                    
                    if not workflow_json:
                        return web.json_response(
                            {'error': 'Workflow JSON is required'},
                            status=400
                        )
                    
                    if not resolutions:
                        return web.json_response(
                            {'error': 'Resolutions array is required'},
                            status=400
                        )
                    
                    # Apply resolutions
                    updated_workflow = apply_resolution(workflow_json, resolutions)
                    
                    return web.json_response({
                        'workflow': updated_workflow,
                        'success': True
                    })
                except Exception as e:
                    self.logger.error(f"Model Linker resolve error: {e}", exc_info=True)
                    return web.json_response(
                        {'error': str(e), 'success': False},
                        status=500
                    )
            
            @routes.get("/model_linker/models")
            async def get_models(request):
                """Get list of all available models (for debugging/UI display)."""
                try:
                    models = get_model_files()
                    return web.json_response(models)
                except Exception as e:
                    self.logger.error(f"Model Linker get_models error: {e}", exc_info=True)
                    return web.json_response(
                        {'error': str(e)},
                        status=500
                    )
            
            self.routes_setup = True
            self.logger.info("Model Linker: API routes registered successfully")
            return True
            
        except ImportError as e:
            self.logger.warning(f"Model Linker: Could not register routes (missing dependency): {e}")
            return False
        except Exception as e:
            self.logger.error(f"Model Linker: Error setting up routes: {e}", exc_info=True)
            return False


# Initialize the extension
try:
    extension = ModelLinkerExtension()
    extension.initialize()
except Exception as e:
    logging.error(f"ComfyUI Model Linker extension initialization failed: {e}", exc_info=True)
