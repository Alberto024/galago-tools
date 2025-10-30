use std::fs;
use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("cargo:warning=Starting proto compilation...");
    
    let mut proto_files = Vec::new();
    
    // Add controller.proto if it exists
    if Path::new("tools/controller.proto").exists() {
        proto_files.push("tools/controller.proto".to_string());
    }
    
    // Automatically discover all proto files in tools/grpc_interfaces/
    let grpc_interfaces_dir = "tools/grpc_interfaces";
    if Path::new(grpc_interfaces_dir).exists() {
        for entry in fs::read_dir(grpc_interfaces_dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.extension().and_then(|s| s.to_str()) == Some("proto") {
                let path_str = path.to_str().unwrap().to_string();
                println!("cargo:warning=Found proto file: {}", path_str);
                proto_files.push(path_str);
            }
        }
    }
    
    if proto_files.is_empty() {
        return Err("No proto files found!".into());
    }
    
    println!("cargo:warning=Compiling {} proto files", proto_files.len());
    
    tonic_build::configure()
        .build_server(false)
        .build_client(true)
        .compile(&proto_files, &["./"])?;
    
    println!("cargo:warning=Proto compilation complete!");
    Ok(())
}
