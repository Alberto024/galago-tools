import logging
import argparse
import threading
import os
import time
from typing import Dict, Any, Callable
from tools.base_server import ToolServer, serve
from tools.grpc_interfaces.bravo_pb2 import Command, Config
from .driver import BravoVWorksDriver

if os.name == "nt":
    import pythoncom

_thread_local = threading.local()


class BravoServer(ToolServer):
    toolType = "bravo"
    config: Config
    
    def __init__(self) -> None:
        super().__init__()
        self.main_thread_id = threading.get_ident()
        logging.info(f"BravoServer initialized in thread ID: {self.main_thread_id}")
        
        # Initialize COM in the main thread
        if os.name == "nt":
            pythoncom.CoInitialize()
            logging.info("COM initialized in main thread")
        
    def _configure(self, request: Config) -> None:
        logging.info(f"Configuring Bravo in thread ID: {threading.get_ident()}")
        self.config = request
        logging.info(f"Bravo configuration complete with device file: {request.device_file}")
    
    def _get_thread_driver(self, force_new: bool = False) -> BravoVWorksDriver:
        """Get or create a driver instance for the current thread"""
        thread_id = threading.get_ident()
        
        # Check if we need to initialize COM for this thread
        if os.name == "nt" and not hasattr(_thread_local, 'com_initialized'):
            logging.info(f"Initializing COM in thread ID: {thread_id}")
            pythoncom.CoInitialize()
            _thread_local.com_initialized = True
        
        # Create or verify existing driver
        if force_new or not hasattr(_thread_local, 'driver'):
            # If we had a previous driver, try to close it properly
            if hasattr(_thread_local, 'driver'):
                try:
                    logging.info(f"Closing previous driver in thread ID: {thread_id}")
                    _thread_local.driver.close()
                except Exception as e:
                    logging.warning(f"Error closing previous driver: {e}")
                
                # Clean up the attribute
                delattr(_thread_local, 'driver')
            
            # Small delay to ensure clean state
            time.sleep(0.1)
            
            # Create new driver
            logging.info(f"Creating new BravoVWorksDriver in thread ID: {thread_id}")
            _thread_local.driver = BravoVWorksDriver(self.config.device_file)
            logging.info(f"BravoVWorksDriver created for thread ID: {thread_id}")
        else:
            # Verify the existing driver is still responsive
            if os.name == "nt":
                try:
                    # Try to pump messages which will fail if COM is disconnected
                    pythoncom.PumpWaitingMessages()
                except Exception as e:
                    logging.warning(f"COM connection test failed, recreating driver: {e}")
                    return self._get_thread_driver(force_new=True)
        
        return _thread_local.driver
    
    def cleanup(self) -> None:
        """Clean up resources properly for all threads"""
        logging.info(f"Cleanup called from thread ID: {threading.get_ident()}")
        
        # Clean up the driver in the current thread if it exists
        if hasattr(_thread_local, 'driver'):
            try:
                logging.info(f"Cleaning up driver for thread ID: {threading.get_ident()}")
                _thread_local.driver.close()
                delattr(_thread_local, 'driver')
            except Exception as e:
                logging.error(f"Error closing driver: {e}")
        
        # Clean up COM in the current thread if it was initialized
        if os.name == "nt" and hasattr(_thread_local, 'com_initialized'):
            try:
                logging.info(f"Uninitializing COM in thread ID: {threading.get_ident()}")
                pythoncom.CoUninitialize()
                delattr(_thread_local, 'com_initialized')
            except Exception as e:
                logging.error(f"Error uninitializing COM: {e}")
    
    def _execute_with_retry(
        self,
        operation_name: str,
        operation_func: Callable[[BravoVWorksDriver], Any],
        max_retries: int = 2
    ) -> Any:
        """Execute an operation with automatic retry on errors
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: Function that takes a BravoVWorksDriver and performs the operation
            max_retries: Maximum number of retry attempts
            
        Returns:
            Result from operation_func
        """
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            try:
                if retries > 0:
                    logging.info(f"Retry #{retries} for {operation_name}")
                    # If we're retrying, force a new driver
                    driver = self._get_thread_driver(force_new=True)
                else:
                    # First attempt uses existing or new driver
                    driver = self._get_thread_driver()
                
                # Process COM messages before running
                if os.name == "nt":
                    pythoncom.PumpWaitingMessages()
                
                # Run the operation
                result = operation_func(driver)
                
                # If we get here, operation succeeded
                return result
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check if this is a COM/RPC error that we should retry
                is_com_error = (
                    "RPC server is unavailable" in error_str or 
                    "marshalled for a different thread" in error_str or
                    "The RPC server is unavailable" in error_str or
                    "COM object" in error_str or
                    "VWorks" in error_str  # VWorks-specific errors
                )
                
                if is_com_error and retries < max_retries:
                    logging.warning(f"COM/VWorks error in {operation_name}: {e}")
                    retries += 1
                    time.sleep(1)  # Wait before retry
                else:
                    # This is not a COM error, or we've exhausted retries
                    if not is_com_error:
                        logging.error(f"Non-COM error in {operation_name}: {e}")
                    else:
                        logging.error(f"Failed {operation_name} after {max_retries} retries")
                    raise
        
        # If we somehow exit the loop without returning or raising
        raise last_error if last_error else RuntimeError(f"Unknown error in {operation_name}")
    
    def ConfigureDeck(self, params: Command.ConfigureDeck) -> None:
        """Initialize Bravo with deck configuration"""
        thread_id = threading.get_ident()
        logging.info(f"ConfigureDeck called from thread ID: {thread_id}")
        
        def config_op(driver: BravoVWorksDriver) -> None:
            # Convert protobuf Struct to Python dict
            deck_config: Dict[int, str] = {}
            if params.deck_configuration:
                for key, value in params.deck_configuration.items():
                    try:
                        position = int(key)
                        labware = str(value)
                        deck_config[position] = labware
                    except (ValueError, TypeError) as e:
                        logging.warning(f"Invalid deck configuration entry: {key}={value}, {e}")
            
            driver.initialize(deck_config)
            logging.info(f"Deck configured with {len(deck_config)} positions")
            return None
        
        self._execute_with_retry("ConfigureDeck", config_op)
    
    def Home(self, params: Command.Home) -> None:
        """Home/initialize axes"""
        thread_id = threading.get_ident()
        logging.info(f"Home called from thread ID: {thread_id}")
        
        def home_op(driver: BravoVWorksDriver) -> None:
            driver.home(axis=params.axis, force=params.force_initialize)
            driver.execute(simulate=False, clear_after_execution=False)
            logging.info(f"Homed axis: {params.axis}")
            return None
        
        self._execute_with_retry("Home", home_op)
    
    def Mix(self, params: Command.Mix) -> None:
        """Mix at location"""
        thread_id = threading.get_ident()
        logging.info(f"Mix called from thread ID: {thread_id}")
        
        def mix_op(driver: BravoVWorksDriver) -> None:
            driver.mix(
                location=params.location,
                volume=params.volume,
                pre_aspirate_volume=params.pre_aspirate_volume,
                blowout_volume=params.blow_out_volume,
                liquid_class=params.liquid_class,
                cycles=params.cycles,
                retract_distance_per_microliter=params.retract_distance_per_microliter,
                pipette_technique=params.pipette_technique,
                aspirate_distance=params.aspirate_distance,
                dispense_distance=params.dispense_distance,
                perform_tip_touch=params.perform_tip_touch,
                tip_touch_side=params.tip_touch_side,
                tip_touch_retract_distance=params.tip_touch_retract_distance,
                tip_touch_horizontal_offset=params.tip_touch_horizonal_offset
            )
            logging.info(f"Mix queued: {params.volume}µL x{params.cycles} at location {params.location}")
            return None
        
        self._execute_with_retry("Mix", mix_op)
    
    def Aspirate(self, params: Command.Aspirate) -> None:
        """Aspirate from location"""
        thread_id = threading.get_ident()
        logging.info(f"Aspirate called from thread ID: {thread_id}")
        
        def aspirate_op(driver: BravoVWorksDriver) -> None:
            driver.aspirate(
                location=params.location,
                volume=params.volume,
                pre_aspirate_volume=params.pre_aspirate_volume,
                post_aspirate_volume=params.post_aspirate_volume,
                liquid_class=params.liquid_class,
                distance_from_well_bottom=params.distance_from_well_bottom,
                retract_distance_per_microliter=params.retract_distance_per_microliter,
                pipette_technique=params.pipette_technique,
                perform_tip_touch=params.perform_tip_touch,
                tip_touch_side=params.tip_touch_side,
                tip_touch_retract_distance=params.tip_touch_retract_distance,
                tip_touch_horizontal_offset=params.tip_touch_horizonal_offset
            )
            logging.info(f"Aspirate queued: {params.volume}µL from location {params.location}")
            return None
        
        self._execute_with_retry("Aspirate", aspirate_op)
    
    def Dispense(self, params: Command.Dispense) -> None:
        """Dispense to location"""
        thread_id = threading.get_ident()
        logging.info(f"Dispense called from thread ID: {thread_id}")
        
        def dispense_op(driver: BravoVWorksDriver) -> None:
            driver.dispense(
                location=params.location,
                empty_tips=params.empty_tips,
                volume=params.volume,
                blowout_volume=params.blow_out_volume,
                liquid_class=params.liquid_class,
                distance_from_well_bottom=params.distance_from_well_bottom,
                retract_distance_per_microliter=params.retract_distance_per_microliter,
                pipette_technique=params.pipette_technique,
                perform_tip_touch=params.perform_tip_touch,
                tip_touch_side=params.tip_touch_side,
                tip_touch_retract_distance=params.tip_touch_retract_distance,
                tip_touch_horizontal_offset=params.tip_touch_horizonal_offset
            )
            logging.info(f"Dispense queued: {params.volume}µL to location {params.location}")
            return None
        
        self._execute_with_retry("Dispense", dispense_op)
    
    def TipsOn(self, params: Command.TipsOn) -> None:
        """Pick up tips at location"""
        thread_id = threading.get_ident()
        logging.info(f"TipsOn called from thread ID: {thread_id}")
        
        def tips_on_op(driver: BravoVWorksDriver) -> None:
            driver.tips_on(params.plate_location)
            logging.info(f"TipsOn queued at location {params.plate_location}")
            return None
        
        self._execute_with_retry("TipsOn", tips_on_op)
    
    def TipsOff(self, params: Command.TipsOff) -> None:
        """Eject tips at location"""
        thread_id = threading.get_ident()
        logging.info(f"TipsOff called from thread ID: {thread_id}")
        
        def tips_off_op(driver: BravoVWorksDriver) -> None:
            driver.tips_off(params.plate_location)
            logging.info(f"TipsOff queued at location {params.plate_location}")
            return None
        
        self._execute_with_retry("TipsOff", tips_off_op)
    
    def MoveToLocation(self, params: Command.MoveToLocation) -> None:
        """Move to specified location"""
        thread_id = threading.get_ident()
        logging.info(f"MoveToLocation called from thread ID: {thread_id}")
        
        def move_op(driver: BravoVWorksDriver) -> None:
            driver.move_to_location(params.plate_location)
            logging.info(f"MoveToLocation queued to location {params.plate_location}")
            return None
        
        self._execute_with_retry("MoveToLocation", move_op)
    
    def ShowDiagnostics(self, params: Command.ShowDiagnostics) -> None:
        """Show diagnostics information"""
        thread_id = threading.get_ident()
        logging.info(f"ShowDiagnostics called from thread ID: {thread_id}")
        
        def diag_op(driver: BravoVWorksDriver) -> None:
            logging.info(f"Device file: {self.config.device_file}")
            logging.info(f"Device name: {driver.builder.device_name}")
            logging.info(f"Initialized: {driver._initialized}")
            logging.info(f"Queued tasks: {len(driver.builder.tasks)}")
            return None
        
        self._execute_with_retry("ShowDiagnostics", diag_op)
    
    def EstimateConfigureDeck(self, params: Command.ConfigureDeck) -> int:
        """Estimate time for ConfigureDeck in seconds"""
        return 10
    
    def EstimateHome(self, params: Command.Home) -> int:
        """Estimate time for Home in seconds"""
        return 15 if 'Z' in params.axis.upper() else 5
    
    def EstimateMix(self, params: Command.Mix) -> int:
        """Estimate time for Mix in seconds"""
        return 5
    
    def EstimateAspirate(self, params: Command.Aspirate) -> int:
        """Estimate time for Aspirate in seconds"""
        return 5
    
    def EstimateDispense(self, params: Command.Dispense) -> int:
        """Estimate time for Dispense in seconds"""
        return 5
    
    def EstimateTipsOn(self, params: Command.TipsOn) -> int:
        """Estimate time for TipsOn in seconds"""
        return 5
    
    def EstimateTipsOff(self, params: Command.TipsOff) -> int:
        """Estimate time for TipsOff in seconds"""
        return 5
    
    def EstimateMoveToLocation(self, params: Command.MoveToLocation) -> int:
        """Estimate time for MoveToLocation in seconds"""
        return 26
    
    def EstimateShowDiagnostics(self, params: Command.ShowDiagnostics) -> int:
        """Estimate time for ShowDiagnostics in seconds"""
        return 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', required=True, help='Port for the gRPC server')
    args = parser.parse_args()
    
    if not args.port:
        raise RuntimeWarning("Port must be provided...")
    
    logging.info("Starting Bravo gRPC server...")
    serve(BravoServer(), str(args.port))