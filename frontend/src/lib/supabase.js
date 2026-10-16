import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://qxiamuzzjkzbctjiycgh.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF4aWFtdXp6amt6YmN0aml5Y2doIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIxNDk0MzgsImV4cCI6MjEwNzcyNTQzOH0.-dxzqms-a3KzX1759I1N9-ACL94YviSCZY2cxt3DjzQ'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
