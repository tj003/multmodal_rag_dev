"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";

export default function HomePage() {
  const { userId } = useAuth();
  const router = useRouter();

    if (userId) {
      router.push("/projects");
    } else {
      router.push("/sign-in");
    }
  }

