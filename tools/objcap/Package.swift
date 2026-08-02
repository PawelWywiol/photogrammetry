// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "objcap",
    platforms: [.macOS(.v15)],
    targets: [
        .executableTarget(name: "objcap", path: "Sources/objcap")
    ]
)
