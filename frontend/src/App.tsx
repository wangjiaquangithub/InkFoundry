import { Button } from "@/components/ui/button";

function App() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-4">InkFoundry Studio</h1>
      <p className="text-muted-foreground mb-8 text-center max-w-md">
        AI-assisted long-form novel generation. The React frontend is initialized with Vite + TypeScript + Tailwind CSS + shadcn/ui.
      </p>
      <div className="flex gap-4">
        <Button>Get Started</Button>
        <Button variant="outline">Documentation</Button>
      </div>
    </div>
  );
}

export default App;
