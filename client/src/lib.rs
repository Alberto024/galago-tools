// Define the structure that mirrors the proto package hierarchy
// The main proto package that contains Command, Config, ToolDriver service, etc.
pub mod com {
    pub mod science {
        pub mod foundry {
            pub mod tools {
                pub mod grpc_interfaces {
                    tonic::include_proto!("com.science.foundry.tools.grpc_interfaces");
                    
                    // Include sub-packages as submodules
                    pub mod toolbox {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.toolbox");
                    }
                    pub mod alps3000 {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.alps3000");
                    }
                    pub mod bioshake {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.bioshake");
                    }
                    pub mod bravo {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.bravo");
                    }
                    pub mod cytation {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.cytation");
                    }
                    pub mod dataman70 {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.dataman70");
                    }
                    pub mod hamilton {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.hamilton");
                    }
                    pub mod hig_centrifuge {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.hig_centrifuge");
                    }
                    pub mod liconic {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.liconic");
                    }
                    pub mod microserve {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.microserve");
                    }
                    pub mod multidrop {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.multidrop");
                    }
                    pub mod opentrons2 {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.opentrons2");
                    }
                    pub mod pf400 {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.pf400");
                    }
                    pub mod plateloc {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.plateloc");
                    }
                    pub mod plr {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.plr");
                    }
                    pub mod pyhamilton {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.pyhamilton");
                    }
                    pub mod spectramax {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.spectramax");
                    }
                    pub mod vcode {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.vcode");
                    }
                    pub mod vprep {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.vprep");
                    }
                    pub mod xpeel {
                        tonic::include_proto!("com.science.foundry.tools.grpc_interfaces.xpeel");
                    }
                }
            }
            
            pub mod controller {
                tonic::include_proto!("com.science.foundry.controller");
            }
        }
    }
}

// Re-export for convenience
pub use com::science::foundry::tools::grpc_interfaces::*;
pub use com::science::foundry::tools::grpc_interfaces::toolbox;
pub use com::science::foundry::controller;