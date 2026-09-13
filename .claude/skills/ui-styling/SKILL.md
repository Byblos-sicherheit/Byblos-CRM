---
name: ui-styling
description: Build beautiful, accessible user interfaces with shadcn/ui components (Radix UI + Tailwind) and Tailwind CSS utility-first styling. Use when implementing UI components, design systems, responsive layouts, accessible components (dialogs, dropdowns, forms, tables, data tables), dark mode, theme customization, or any React/Next.js component work. Triggers on "shadcn", "tailwind", "ui component", "dialog", "form", "data table", "dark mode", "theme", "responsive layout", "component library".
argument-hint: "[component or layout to build]"
---

# UI Styling — shadcn/ui + Tailwind CSS

Production-ready UI component skill. Combines shadcn/ui (Radix UI primitives) with Tailwind CSS for accessible, themeable interfaces.

## Stack

| Layer | Tool | Purpose |
|---|---|---|
| Components | shadcn/ui (Radix UI) | Accessible primitives, copy-paste model |
| Styling | Tailwind CSS v4 | Utility-first, build-time, zero runtime |
| Forms | react-hook-form + zod | Validated, typed forms |
| State | React / Next.js | Component and server state |

## Setup

```bash
# Init shadcn/ui (configures Tailwind automatically)
npx shadcn@latest init

# Add components
npx shadcn@latest add button card dialog form table input select
```

**Tailwind-only (no shadcn):**
```bash
npm install -D tailwindcss @tailwindcss/vite
```
```js
// vite.config.ts
import tailwindcss from '@tailwindcss/vite'
export default { plugins: [tailwindcss()] }
```
```css
/* src/index.css */
@import "tailwindcss";
```

## Core Component Patterns

### Card Layout
```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function FeatureCard() {
  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <CardTitle className="text-2xl font-bold">Analytics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-muted-foreground">View your metrics</p>
        <Button className="w-full">View Details</Button>
      </CardContent>
    </Card>
  )
}
```

### Form with Validation
```tsx
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

export function LoginForm() {
  const form = useForm({ resolver: zodResolver(schema) })
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(console.log)} className="space-y-6">
        <FormField control={form.control} name="email" render={({ field }) => (
          <FormItem>
            <FormLabel>Email</FormLabel>
            <FormControl><Input type="email" {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <Button type="submit" className="w-full">Sign In</Button>
      </form>
    </Form>
  )
}
```

### Responsive Grid + Dark Mode
```tsx
<div className="min-h-screen bg-white dark:bg-gray-900">
  <div className="container mx-auto px-4 py-8">
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
        <CardContent className="p-6">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Content</h3>
        </CardContent>
      </Card>
    </div>
  </div>
</div>
```

### Data Table
```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export function DataTable({ data }: { data: Record<string, string>[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Amount</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row, i) => (
          <TableRow key={i}>
            <TableCell className="font-medium">{row.name}</TableCell>
            <TableCell>{row.status}</TableCell>
            <TableCell className="text-right">{row.amount}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

### Dialog / Modal
```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

export function ConfirmDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">Open</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Confirm Action</DialogTitle>
        </DialogHeader>
        <div className="py-4">Are you sure?</div>
        <div className="flex gap-2 justify-end">
          <Button variant="outline">Cancel</Button>
          <Button>Confirm</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

## Tailwind Quick Reference

### Layout
```
flex items-center justify-between gap-4
grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-6
container mx-auto px-4 max-w-7xl
```

### Spacing Scale
```
p-2=8px  p-4=16px  p-6=24px  p-8=32px  p-12=48px  p-16=64px
```

### Typography
```
text-sm/base/lg/xl/2xl/3xl/4xl
font-normal/medium/semibold/bold
text-gray-900 dark:text-white
text-muted-foreground  (shadcn semantic)
```

### Colors (shadcn CSS variables)
```css
--background       /* page background */
--foreground       /* page text */
--primary          /* primary action color */
--primary-foreground
--muted            /* subtle backgrounds */
--muted-foreground /* secondary text */
--border           /* borders */
--destructive      /* errors / delete */
```

### Common Utilities
```
rounded-md rounded-lg rounded-full
shadow-sm shadow-md shadow-lg
transition-all duration-200 ease-in-out
hover:bg-accent focus-visible:ring-2
```

## Theme Customization

**globals.css:**
```css
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --radius: 0.5rem;
  }
  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
  }
}
```

**Dark mode with next-themes:**
```tsx
// app/layout.tsx
import { ThemeProvider } from "next-themes"
export default function Layout({ children }) {
  return <ThemeProvider attribute="class" defaultTheme="system" enableSystem>{children}</ThemeProvider>
}
```

## Accessibility Checklist

- [ ] All interactive elements reachable by keyboard (Tab/Enter/Space/Esc)
- [ ] Focus ring visible (`focus-visible:ring-2`)
- [ ] Contrast ratio ≥ 4.5:1 for normal text, ≥ 3:1 for large text
- [ ] Icon-only buttons have `aria-label`
- [ ] Form inputs linked to labels (`<FormLabel>` in shadcn)
- [ ] Error messages associated with fields (`aria-describedby`)
- [ ] Dialogs trap focus, close on Esc
- [ ] Touch targets ≥ 44×44px

## RTL Support (Arabic / Byblos CRM)

```html
<!-- Set direction on root -->
<html dir="rtl" lang="ar">
```

```tsx
// Tailwind logical properties (RTL-aware)
className="ms-4"   // margin-inline-start (→ margin-right in RTL)
className="ps-4"   // padding-inline-start
className="text-start"  // text-align: start
className="border-s"    // border-inline-start

// Override per-direction
className="ltr:mr-4 rtl:ml-4"
```

## Component Catalog (shadcn)

| Category | Components |
|---|---|
| Form & Input | Button, Input, Textarea, Select, Checkbox, RadioGroup, Switch, Slider, DatePicker |
| Layout | Card, Separator, Aspect Ratio, ScrollArea |
| Navigation | NavigationMenu, Tabs, Breadcrumb, Pagination |
| Overlays | Dialog, Drawer, Sheet, Popover, Tooltip, HoverCard |
| Feedback | Alert, Toast (Sonner), Progress, Skeleton, Badge |
| Display | Table, Avatar, Calendar, Command |

## Best Practices

1. **Utility-first** — Use Tailwind classes directly; extract components only for true repetition
2. **Semantic tokens** — Use CSS variables (`var(--primary)`), never raw hex in components  
3. **Mobile-first** — Write base styles for mobile, add `md:` and `lg:` breakpoints
4. **Composition** — Build complex UI from simple Radix primitives
5. **Type safety** — TypeScript for all component props
6. **No dynamic class names** — Tailwind purges unused classes; avoid `className={`text-${color}`}`
