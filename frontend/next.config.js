/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
        // NEXT_PUBLIC_API_URL dùng cho client-side, API_URL dùng cho server-side rewrites
        const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        return [
            {
                source: "/api/:path*",
                destination: `${apiUrl}/api/:path*`,
            },
        ];
    },
    output: "standalone",
};

module.exports = nextConfig;
