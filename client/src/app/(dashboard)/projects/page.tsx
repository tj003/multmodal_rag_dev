"use client"

import React, { use } from 'react'
import {useEffect, useState} from "react"
import {useAuth} from "@clerk/nextjs"
import {useRouter} from "next/navigation"

import { ProjectsGrid } from '@/components/projects/ProjectsGrid'
import { CreateProjectModal } from '@/components/projects/CreateProjectModal'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import toast from 'react-hot-toast'


const ProjectsPage = () => {
  // Datat state

  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  //UI state
  const [searchQuery, setSearchQuery] = useState("")
  const [viewMode, setViewMode] = useState("grid")

  //Modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [isCreating, setIsCreating] = useState(false)

  const {getToken, userId} = useAuth()
  const router = useRouter()

  // Business logic functions
  const loadPro
  return (
    <div></div>
  )
}

export default ProjectsPage
