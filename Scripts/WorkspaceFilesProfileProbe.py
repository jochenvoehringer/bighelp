"""Exercise the production Files composition with SwiftUI on macOS.

Usage: python3 Scripts/WorkspaceFilesProfileProbe.py [repository]

Compiles the unchanged RootShellView Files factory methods and the complete
ConfiguredWorkspaceArtifactsView. AppKit hosts the real SwiftUI view, including
its task, state, identity and observation. App/network dependencies are narrow
in-memory doubles; no host, login, package resolution or app installation is used.
This is a composition regression probe, not a transport or signed-app test.
"""
from pathlib import Path
import subprocess
import tempfile
import sys

repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
root = (repo / 'Bighelp/App/RootAgentHome.swift').read_text()
start = root.index('    /// Picks the agent\'s workspace folder')
end = root.index('    // MARK: Board data', start)
view = (repo / 'Bighelp/WorkspaceManagement/ConfiguredWorkspaceArtifactsView.swift').read_text()
scaffold = r'''
import AppKit
import SwiftUI
import Observation

struct WorkspaceOwner: Equatable, Hashable { let id: Int }
struct AgentProfile { let id: String }
struct NativeContext { let servingProfileID = "default" }
@MainActor protocol DirectHermesNativeHTTP: AnyObject {}
@MainActor protocol DirectHermesAuthenticatedHTTP: AnyObject {}
@MainActor protocol WorkspaceOperationPerforming: AnyObject {}
enum WorkspaceClientError: Error {
 case unavailable(Availability), rejected(String?, String?)
 enum Availability { case unsupportedOperation, pluginRequired }
 static func workspaceFilesMessage(_ code: String?) -> String? { nil }
}
enum DirectHermesManagedFilesError: Error { case invalidResponse }
struct DirectHermesWorkspaceFileScope { let root: String; let owner: WorkspaceOwner }
@MainActor @Observable final class ProbeHTTP: DirectHermesNativeHTTP, DirectHermesAuthenticatedHTTP {
 var scopeAgents: [String?] = []
 var artifactAgents: [String?] = []
 var currentChecks: [@MainActor () -> WorkspaceOwner?] = []
 var delay = false
 var pending: CheckedContinuation<Void, Never>?
}
@MainActor final class DirectHermesManagedFilesClient {
 let http: ProbeHTTP; let owner: WorkspaceOwner; let agentID: String?
 let currentOwner: @MainActor () -> WorkspaceOwner?
 init(http: any DirectHermesNativeHTTP & DirectHermesAuthenticatedHTTP, owner: WorkspaceOwner,
      agentID: String? = nil, currentOwner: @escaping @MainActor () -> WorkspaceOwner?) {
  self.http = http as! ProbeHTTP; self.owner = owner; self.agentID = agentID; self.currentOwner = currentOwner
 }
 func workspaceScope() async throws -> DirectHermesWorkspaceFileScope {
  http.scopeAgents.append(agentID)
  http.currentChecks.append(currentOwner)
  if http.delay { await withCheckedContinuation { http.pending = $0 } }
  return .init(root: "/srv/" + (agentID ?? "default"), owner: owner)
 }
}
@MainActor final class DirectHermesArtifactClient {
 init(http: any DirectHermesNativeHTTP & DirectHermesAuthenticatedHTTP, owner: WorkspaceOwner,
      fallback: any WorkspaceOperationPerforming, agentID: String? = nil,
      currentOwner: @escaping @MainActor () -> WorkspaceOwner?) {
  (http as! ProbeHTTP).artifactAgents.append(agentID)
 }
}
@MainActor final class DirectHermesWorkspaceClient: WorkspaceOperationPerforming {
 let nativeContext: NativeContext? = NativeContext()
}
struct SelectedWorkspace { let nativeClient: ProbeHTTP }
struct Hosts { let selectedWorkspace: SelectedWorkspace? }
@MainActor @Observable final class Connections {
 var workspace: (any WorkspaceOperationPerforming)? = DirectHermesWorkspaceClient()
 let hosts: Hosts
 var selectedAgent = "research"
 init(_ http: ProbeHTTP) { hosts = Hosts(selectedWorkspace: SelectedWorkspace(nativeClient: http)) }
}
@MainActor struct WorkspaceFolderChooser {
 let profileID: String
 static func live(client: DirectHermesWorkspaceClient, owner: WorkspaceOwner, profileID: String) -> Self {
  Self(profileID: profileID)
 }
 static func canFix(_ error: Error) -> Bool { false }
}
@MainActor struct WorkspaceFolderPicker: View {
 let chooser: WorkspaceFolderChooser; let onChosen: () -> Void
 var body: some View { EmptyView() }
}
enum SheetSize { case standard }
extension View {
 func bighelpSheet<V: View>(isPresented: Binding<Bool>, @ViewBuilder content: () -> V) -> some View { self }
 func bighelpSheetSize(_ size: SheetSize) -> some View { self }
}
@MainActor struct WorkspaceArtifactsView: View {
 let hostName: String; let owner: WorkspaceOwner; let scope: DirectHermesWorkspaceFileScope
 let performer: DirectHermesArtifactClient
 let scopeValidator: () async throws -> DirectHermesWorkspaceFileScope
 let isCurrent: () -> Bool; let isEmbedded: Bool
 var body: some View { Text(scope.root) }
}
@MainActor struct RootShellView: View {
 let workspaceConnections: Connections?
 var currentWorkspaceOwner: WorkspaceOwner? { WorkspaceOwner(id: 1) }
 var workspaceHostName: String { "Fixture" }
 var homeAgent: AgentProfile? { workspaceConnections.map { AgentProfile(id: $0.selectedAgent) } }
 var body: some View { appsArtifacts }
}
'''
runner = r'''
@main struct Probe {
 @MainActor static func main() {
  let app = NSApplication.shared
  app.setActivationPolicy(.accessory)
  let http = ProbeHTTP()
  let connections = Connections(http)
  let root = RootShellView(workspaceConnections: connections)
  let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 400, height: 250),
                        styleMask: [.titled], backing: .buffered, defer: false)
  window.contentView = NSHostingView(rootView: root)
  window.orderFront(nil)
  Task { @MainActor in
   var failures = 0
   func check(_ condition: Bool, _ name: String) {
    print("\(condition ? "PASS" : "FAIL") \(name)")
    if !condition { failures += 1 }
   }
   @MainActor func waitFor(_ predicate: @MainActor () -> Bool) async {
    for _ in 0..<100 {
     if predicate() { return }
     try? await Task.sleep(for: .milliseconds(20))
    }
   }
   await waitFor { !http.artifactAgents.isEmpty }
   check(http.scopeAgents.first.flatMap { $0 } == "research", "selected agent reaches scope client")
   check(http.artifactAgents.first.flatMap { $0 } == "research", "selected agent reaches artifact client")
   check(root.workspaceFolderChooser(owner: WorkspaceOwner(id: 1))?.profileID == "research",
         "folder chooser targets selected agent rather than serving agent")
   let previousCheck = http.currentChecks.first
   connections.selectedAgent = "default"
   await waitFor { http.artifactAgents.count >= 2 }
   check(http.scopeAgents.count >= 2 && http.scopeAgents.last.flatMap { $0 } == "default",
         "switching agent reloads scope on the same host")
   check(previousCheck?() == nil, "previous agent loses ownership after switch")
   http.delay = true
   connections.selectedAgent = "writer"
   await waitFor { http.pending != nil }
   check(http.pending != nil, "delayed scope starts for next agent")
   connections.selectedAgent = "default"
   let before = http.artifactAgents.count
   http.delay = false
   http.pending?.resume()
   http.pending = nil
   try? await Task.sleep(for: .milliseconds(250))
   check(!http.artifactAgents.dropFirst(before).contains(where: { $0 == "writer" }),
         "late previous-agent scope cannot create its artifact client")
   window.orderOut(nil)
   exit(failures == 0 ? 0 : 1)
  }
  app.run()
 }
}
'''
with tempfile.TemporaryDirectory(prefix='bighelp-routing-') as folder:
 p = Path(folder)
 (p / 'Probe.swift').write_text(scaffold + '\nextension RootShellView {\n' + root[start:end] + '\n}\n' + view + runner)
 subprocess.run(['swiftc', '-parse-as-library', '-swift-version', '6', str(p / 'Probe.swift'), '-o', str(p / 'probe')], check=True)
 sys.exit(subprocess.run([str(p / 'probe')], timeout=20).returncode)
