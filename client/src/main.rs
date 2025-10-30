use anyhow::{Context, Result};
use tonic::Request;
use lab_tools_client::*;
use clap::{Parser, Subcommand};

pub struct ToolClient {
    client: tool_driver_client::ToolDriverClient<tonic::transport::Channel>,
}

impl ToolClient {
    pub async fn new(address: &str) -> Result<Self> {
        let client = tool_driver_client::ToolDriverClient::connect(address.to_string())
            .await
            .context(format!("Failed to connect to {}", address))?;
        
        Ok(Self { client })
    }

    pub async fn get_status(&mut self) -> Result<StatusReply> {
        let request = Request::new(());
        let response = self.client.get_status(request).await?;
        Ok(response.into_inner())
    }

    pub async fn run_script(&mut self, script: &str, blocking: bool) -> Result<String> {
        let script_cmd = toolbox::command::RunScript {
            script_content: script.to_string(),
            blocking,
        };
        
        let toolbox_cmd = toolbox::Command {
            command: Some(toolbox::command::Command::RunScript(script_cmd)),
        };
        
        let base_command = Command {
            tool_command: Some(command::ToolCommand::Toolbox(toolbox_cmd)),
        };
        
        let response = self.client.execute_command(Request::new(base_command)).await?;
        let reply = response.into_inner();
        
        // SUCCESS = 1 in the proto
        if reply.response != 1 {
            anyhow::bail!("Script execution failed. Code: {}, Error: {:?}", 
                         reply.response, reply.error_message);
        }
        
        // Extract the response from metadata
        if let Some(metadata) = reply.meta_data {
            if let Some(response_field) = metadata.fields.get("response") {
                if let Some(kind) = &response_field.kind {
                    use prost_types::value::Kind;
                    match kind {
                        Kind::StringValue(s) => return Ok(s.clone()),
                        Kind::NumberValue(n) => return Ok(n.to_string()),
                        Kind::BoolValue(b) => return Ok(b.to_string()),
                        Kind::NullValue(_) => return Ok("null".to_string()),
                        _ => return Ok(format!("{:?}", kind)),
                    }
                }
            }
        }
        
        Ok("Script executed (no output)".to_string())
    }
}

#[derive(Parser)]
#[command(name = "lab-tools-client")]
#[command(about = "Rust gRPC client for lab automation tools", long_about = None)]
struct Cli {
    /// Server address
    #[arg(short, long, default_value = "http://127.0.0.1:50051")]
    server: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Check server status
    Status,
    
    /// Execute a Python script
    Exec {
        /// Python script to execute
        #[arg(short, long)]
        script: String,
        
        /// Wait for script completion
        #[arg(short, long, default_value = "true")]
        blocking: bool,
    },
    
    /// Run interactive Python REPL (experimental)
    Repl,
    
    /// Run built-in demo/tests
    Demo,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();
    
    let cli = Cli::parse();
    
    let mut client = ToolClient::new(&cli.server).await?;
    
    match cli.command {
        Commands::Status => {
            println!("Checking server status...");
            let status = client.get_status().await?;
            println!("\n✓ Server Status:");
            println!("  State: {} (3=READY)", status.status);
            println!("  Uptime: {} seconds", status.uptime);
            if let Some(err) = status.error_message {
                if !err.is_empty() {
                    println!("  Error: {}", err);
                }
            }
        }
        
        Commands::Exec { script, blocking } => {
            println!("Executing Python script...\n");
            let result = client.run_script(&script, blocking).await?;
            println!("Output:\n{}", result);
        }
        
        Commands::Repl => {
            println!("=== Interactive Python REPL ===");
            println!("Type Python code and press Enter. Type 'exit' or Ctrl+C to quit.\n");
            
            use std::io::{self, Write};
            loop {
                print!(">>> ");
                io::stdout().flush()?;
                
                let mut input = String::new();
                io::stdin().read_line(&mut input)?;
                
                let trimmed = input.trim();
                if trimmed == "exit" || trimmed == "quit" {
                    println!("Goodbye!");
                    break;
                }
                
                if trimmed.is_empty() {
                    continue;
                }
                
                match client.run_script(trimmed, true).await {
                    Ok(result) => {
                        if !result.is_empty() {
                            println!("{}", result);
                        }
                    }
                    Err(e) => println!("Error: {}", e),
                }
            }
        }
        
        Commands::Demo => {
            println!("=== Lab Tools Demo ===\n");
            
            println!("--- Test 1: Simple Print ---");
            let result = client.run_script(r#"print("Hello from Rust!")"#, true).await?;
            println!("✓ {}\n", result);

            println!("--- Test 2: Calculation ---");
            let result = client.run_script(r#"print(f"42 + 58 = {42 + 58}")"#, true).await?;
            println!("✓ {}\n", result);

            println!("--- Test 3: System Info ---");
            let script = r#"
import sys
import platform
print(f"Python {sys.version.split()[0]}")
print(f"Platform: {platform.platform()}")
"#;
            let result = client.run_script(script, true).await?;
            println!("✓ {}\n", result);

            println!("🎉 All tests passed!");
        }
    }
    
    Ok(())
}