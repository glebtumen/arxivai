import Link from "next/link";

export default function NotFound() {
    return (
        <div className="text-center">
            <h2 className="mb-2 text-xl font-semibold">Item not found</h2>
            <p className="mb-4 text-slate-500">
                This item doesn&apos;t exist or hasn&apos;t finished processing yet.
            </p>
            <Link href="/" className="text-blue-600">
                ← Back to library
            </Link>
        </div>
    );
}
