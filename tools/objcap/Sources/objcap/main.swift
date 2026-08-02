import Foundation
import RealityKit

// objcap — thin CLI over Apple RealityKit PhotogrammetrySession (Object Capture).
// Input: folder of HEIC/JPEG. Output: .usdz file, or a directory receiving OBJ+USDA+textures.

struct Options {
    var input: URL
    var output: URL
    var detail: PhotogrammetrySession.Request.Detail = .full
    var ordering: PhotogrammetrySession.Configuration.SampleOrdering = .unordered
    var sensitivity: PhotogrammetrySession.Configuration.FeatureSensitivity = .normal
    var masking = true
    var polygonCount: UInt = 0
    var textureDimension: PhotogrammetrySession.Configuration.CustomDetailSpecification.TextureDimension = .fourK
    var checkpoint: URL?
}

let usage = """
usage: objcap <input-images-dir> <output.usdz | output-dir> [options]

options:
  --detail <preview|reduced|medium|full|raw|custom>   default: full
  --order <unordered|sequential>                      default: unordered
  --sensitivity <normal|high>                         default: normal
  --no-masking                                        disable automatic object masking
  --polygons <n>                                      target polygon count (implies --detail custom)
  --texture <1k|2k|4k|8k|16k>                         custom-detail texture size, default: 4k
  --checkpoint <dir>                                  reusable working dir (faster re-runs)

An output path ending in .usdz writes a single USDZ. Any other path is treated as a
directory and receives OBJ + USDA + texture maps.
"""

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n\n\(usage)\n".utf8))
    exit(1)
}

func parseArgs() -> Options {
    var positional: [String] = []
    var flags: [String: String] = [:]
    var args = Array(CommandLine.arguments.dropFirst())
    while let arg = args.first {
        args.removeFirst()
        guard arg.hasPrefix("--") else { positional.append(arg); continue }
        if arg == "--no-masking" { flags[arg] = "true"; continue }
        guard let value = args.first else { fail("missing value for \(arg)") }
        args.removeFirst()
        flags[arg] = value
    }
    guard positional.count == 2 else { fail("expected 2 positional arguments, got \(positional.count)") }

    // RealityKit decides "single file" vs "OBJ+USDA folder" from URL.hasDirectoryPath,
    // which must be set explicitly — it is not inferred from the filesystem.
    let outputPath = positional[1]
    let extension_ = (outputPath as NSString).pathExtension.lowercased()
    var options = Options(
        input: URL(fileURLWithPath: positional[0], isDirectory: true),
        output: URL(fileURLWithPath: outputPath,
                    isDirectory: !["usdz", "json"].contains(extension_))
    )

    for (flag, value) in flags {
        switch flag {
        case "--detail":
            let map: [String: PhotogrammetrySession.Request.Detail] = [
                "preview": .preview, "reduced": .reduced, "medium": .medium,
                "full": .full, "raw": .raw, "custom": .custom,
            ]
            guard let detail = map[value] else { fail("unknown detail: \(value)") }
            options.detail = detail
        case "--order":
            guard let ordering = ["unordered": PhotogrammetrySession.Configuration.SampleOrdering.unordered,
                                  "sequential": .sequential][value] else { fail("unknown order: \(value)") }
            options.ordering = ordering
        case "--sensitivity":
            guard let sensitivity = ["normal": PhotogrammetrySession.Configuration.FeatureSensitivity.normal,
                                     "high": .high][value] else { fail("unknown sensitivity: \(value)") }
            options.sensitivity = sensitivity
        case "--no-masking":
            options.masking = false
        case "--polygons":
            guard let count = UInt(value), count > 0 else { fail("invalid polygon count: \(value)") }
            options.polygonCount = count
            options.detail = .custom
        case "--texture":
            let map: [String: PhotogrammetrySession.Configuration.CustomDetailSpecification.TextureDimension] = [
                "1k": .oneK, "2k": .twoK, "4k": .fourK, "8k": .eightK, "16k": .sixteenK,
            ]
            guard let dimension = map[value] else { fail("unknown texture size: \(value)") }
            options.textureDimension = dimension
        case "--checkpoint":
            options.checkpoint = URL(fileURLWithPath: value)
        default:
            fail("unknown flag: \(flag)")
        }
    }
    return options
}

func log(_ message: String) {
    print("[objcap] \(message)")
    fflush(stdout)
}

let options = parseArgs()

guard PhotogrammetrySession.isSupported else {
    fail("PhotogrammetrySession is not supported on this machine")
}

let limits = PhotogrammetrySession.limits
log("limits: max \(limits.maximumNumberOfInputImages) images, max dimension \(limits.maximumInputImageDimension)px")

var configuration = options.checkpoint.map { checkpoint -> PhotogrammetrySession.Configuration in
    try? FileManager.default.createDirectory(at: checkpoint, withIntermediateDirectories: true)
    return PhotogrammetrySession.Configuration(checkpointDirectory: checkpoint)
} ?? PhotogrammetrySession.Configuration()

configuration.sampleOrdering = options.ordering
configuration.featureSensitivity = options.sensitivity
configuration.isObjectMaskingEnabled = options.masking
if options.detail == .custom {
    configuration.customDetailSpecification.maximumPolygonCount = options.polygonCount > 0 ? options.polygonCount : 250_000
    configuration.customDetailSpecification.maximumTextureDimension = options.textureDimension
}

let isPosesRequest = options.output.pathExtension.lowercased() == "json"
let isSingleFile = options.output.pathExtension.lowercased() == "usdz"
let outputParent = (isSingleFile || isPosesRequest)
    ? options.output.deletingLastPathComponent() : options.output
try? FileManager.default.createDirectory(at: outputParent, withIntermediateDirectories: true)

let session: PhotogrammetrySession
do {
    session = try PhotogrammetrySession(input: options.input, configuration: configuration)
} catch {
    fail("cannot open session: \(error.localizedDescription)")
}

// A `poses` request solves camera alignment only — no meshing, no texturing. It is the
// cheapest way to learn which photos the solver could actually place, and where.
let request = isPosesRequest
    ? PhotogrammetrySession.Request.poses
    : PhotogrammetrySession.Request.modelFile(url: options.output, detail: options.detail)
log("input: \(options.input.path)")
log("output: \(options.output.path) (\(isSingleFile ? "usdz" : "obj+usda directory"))")
log("detail: \(options.detail), ordering: \(options.ordering), sensitivity: \(options.sensitivity), masking: \(options.masking)")

let start = Date()
var lastPercent = -1

do {
    try session.process(requests: [request])
} catch {
    fail("cannot start processing: \(error.localizedDescription)")
}

for try await output in session.outputs {
    switch output {
    case .requestProgress(_, let fraction):
        let percent = Int(fraction * 100)
        if percent != lastPercent {
            lastPercent = percent
            log("progress \(percent)%")
        }
    case .requestProgressInfo(_, let info):
        let stage = info.processingStage.map { "\($0)" } ?? "?"
        let eta = info.estimatedRemainingTime.map { " eta \(Int($0))s" } ?? ""
        log("stage: \(stage)\(eta)")
    case .requestComplete(_, let result):
        if case .modelFile(let url) = result { log("written: \(url.path)") }
        if case .poses(let poses) = result {
            let urls = poses.urlsBySample
            let entries = poses.posesBySample.keys.sorted().map { id -> [String: Any] in
                let pose = poses.posesBySample[id]!
                return [
                    "id": id,
                    "file": urls[id]?.lastPathComponent ?? "",
                    "translation": [pose.translation.x, pose.translation.y, pose.translation.z],
                    "rotation": [pose.rotation.vector.x, pose.rotation.vector.y,
                                 pose.rotation.vector.z, pose.rotation.vector.w],
                ]
            }
            let data = try JSONSerialization.data(withJSONObject: ["poses": entries],
                                                  options: [.prettyPrinted, .sortedKeys])
            try data.write(to: options.output)
            log("written: \(options.output.path) (\(entries.count) camera poses)")
        }
    case .requestError(_, let error):
        fail("request failed: \(error.localizedDescription)")
    case .inputComplete:
        log("all input images ingested")
    case .invalidSample(let id, let reason):
        log("invalid sample \(id): \(reason)")
    case .skippedSample(let id):
        log("skipped sample \(id)")
    case .automaticDownsampling:
        log("images were automatically downsampled")
    case .stitchingIncomplete:
        log("warning: stitching incomplete — some views could not be aligned")
    case .processingComplete:
        log("done in \(Int(Date().timeIntervalSince(start)))s")
        exit(0)
    case .processingCancelled:
        fail("processing cancelled")
    @unknown default:
        break
    }
}
