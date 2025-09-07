"""
CrewAI agents for infrastructure planning and execution
"""

from crewai import Agent, Task, Crew, Process
from langchain_ollama import OllamaLLM

class InfraCrew:
    """CrewAI-based infrastructure management crew"""

    def __init__(self, ollama_client, memory, model="deepseek-coder"):
        self.memory = memory
        self.model = model

        # Initialize Ollama LLM for CrewAI (using new langchain-ollama package)
        # CrewAI now uses litellm which requires provider prefix
        ollama_model = f"ollama/{model}"
        self.llm = OllamaLLM(
            model=ollama_model,
            base_url="http://localhost:11434",
            temperature=0.1
        )

        # Initialize agents
        self.planner = self._create_planner_agent()
        self.executor = self._create_executor_agent()
        self.reviewer = self._create_reviewer_agent()

        # Define tasks (will be created in execute_task method)
        self.agents_list = [self.planner, self.executor, self.reviewer]

    def _create_planner_agent(self):
        """Create the planning agent"""
        return Agent(
            role="Infrastructure Planner",
            goal="Analyze infrastructure tasks and create execution plans",
            backstory="""You are an expert DevOps engineer specializing in infrastructure automation.
            You excel at breaking down complex infrastructure tasks into actionable steps and
            determining the best approach using Ansible, shell commands, or other tools.""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

    def _create_executor_agent(self):
        """Create the execution agent"""
        return Agent(
            role="Ansible Playbook Generator",
            goal="Generate Ansible playbooks and shell commands to execute infrastructure tasks",
            backstory="""You are a master of infrastructure automation with deep expertise in Ansible,
            Linux system administration, and DevOps best practices. You write clean, idempotent
            Ansible playbooks and efficient shell commands that follow security best practices.""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

    def _create_reviewer_agent(self):
        """Create the review agent"""
        return Agent(
            role="Infrastructure Reviewer",
            goal="Review and validate infrastructure automation before execution",
            backstory="""You are a security-conscious infrastructure reviewer who ensures that
            all automation is safe, follows best practices, and won't cause system damage.
            You catch potential issues before they become problems.""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

    def execute_task(self, task_description: str, context: list = None) -> dict:
        """Execute a task using the agent crew"""

        # Prepare context from memory
        context_str = ""
        if context:
            successful_playbooks = [c for c in context if c.get("type") == "playbook"
                                  and c.get("metadata", {}).get("success")]
            if successful_playbooks:
                context_str = f"\n\nRelevant past successful approaches:\n"
                for pb in successful_playbooks[:2]:  # Limit context
                    context_str += f"Task: {pb['metadata'].get('task', 'N/A')}\n"
                    context_str += f"Solution: {pb['content'][:500]}...\n\n"

        # Create planning task
        planning_task = Task(
            description=f"""
            Analyze this infrastructure task: "{task_description}"

            Requirements:
            1. Break down the task into specific, actionable steps
            2. Identify what systems/services will be affected
            3. Determine the best automation approach (Ansible playbook vs shell commands)
            4. Consider security implications and safety measures
            5. Plan for verification and rollback if needed

            {context_str}

            Provide a detailed execution plan with clear steps.
            """,
            agent=self.planner,
            expected_output="A detailed execution plan with numbered steps and chosen approach"
        )

        # Create execution task
        execution_task = Task(
            description=f"""
            Based on the planning agent's analysis, generate the actual automation code for: "{task_description}"

            Requirements:
            1. If Ansible is appropriate, create a complete, idempotent playbook
            2. If shell commands are better, provide safe, tested commands
            3. Include error handling and verification steps
            4. Follow security best practices
            5. Make it production-ready

            Format your response as:
            APPROACH: [Ansible/Shell/Mixed]

            PLAYBOOK/COMMANDS:
            [Your generated code here]

            VERIFICATION:
            [How to verify success]
            """,
            agent=self.executor,
            expected_output="Complete automation code (Ansible playbook or shell commands) ready for execution"
        )

        # Create review task
        review_task = Task(
            description=f"""
            Review the generated automation for the task: "{task_description}"

            Check for:
            1. Security vulnerabilities or risky operations
            2. Idempotency and reliability
            3. Error handling and rollback capabilities
            4. Best practices compliance
            5. Potential for system damage

            If issues found, provide specific fixes.
            If approved, confirm it's ready for execution.

            Format your response as:
            STATUS: [APPROVED/NEEDS_FIXES]

            ISSUES: [List any problems found]

            FIXES: [Specific corrections needed]

            FINAL_CODE: [The corrected/approved code]
            """,
            agent=self.reviewer,
            expected_output="Security and quality review with final approved automation code"
        )

        # Create crew with tasks and execute
        crew = Crew(
            agents=self.agents_list,
            tasks=[planning_task, execution_task, review_task],
            process=Process.sequential,
            verbose=False
        )

        crew_result = crew.kickoff()

        # Parse results
        result = self._parse_crew_result(crew_result, task_description)

        return result

    def _parse_crew_result(self, crew_result, task_description: str) -> dict:
        """Parse the crew execution result"""
        # Handle CrewOutput object from newer CrewAI versions
        if hasattr(crew_result, 'raw'):
            raw_output = crew_result.raw
        elif hasattr(crew_result, 'result'):
            raw_output = crew_result.result
        else:
            raw_output = str(crew_result)

        result = {
            "task": task_description,
            "raw_output": raw_output,
            "playbook_content": None,
            "approach": "unknown",
            "status": "completed"
        }

        try:
            # Extract the final result from the review agent
            lines = raw_output.split('\n')
            current_section = None
            final_code_lines = []

            for line in lines:
                line = line.strip()

                if line.startswith('STATUS:'):
                    result['review_status'] = line.replace('STATUS:', '').strip()
                elif line.startswith('APPROACH:'):
                    result['approach'] = line.replace('APPROACH:', '').strip().lower()
                elif line.startswith('RESULT:') or line.startswith('OUTPUT:'):
                    result['actual_result'] = line.replace('RESULT:', '').replace('OUTPUT:', '').strip()
                elif line.startswith('FINAL_CODE:'):
                    current_section = 'final_code'
                elif current_section == 'final_code' and line:
                    final_code_lines.append(line)

            # If we have final code, use it as the playbook content
            if final_code_lines:
                result['playbook_content'] = '\n'.join(final_code_lines)
            else:
                # Fallback: try to extract playbook from the full output
                # Look for YAML content indicators
                if any(indicator in raw_output.lower() for indicator in ['yaml', 'playbook', 'hosts:', 'tasks:', '---']):
                    # Extract YAML-like content - look for common patterns
                    yaml_start = False
                    playbook_lines = []
                    in_yaml_block = False

                    for line in lines:
                        line_strip = line.strip()

                        # Start of YAML block
                        if line_strip.startswith('---') or (line_strip.startswith('hosts:') or 'hosts: localhost' in line):
                            yaml_start = True
                            in_yaml_block = True
                            playbook_lines.append(line)
                        # Continue collecting YAML
                        elif yaml_start and (line.startswith(' ') or line_strip.startswith('- name:') or
                                           line_strip.startswith('tasks:') or line_strip.startswith('become:') or
                                           line_strip.startswith('- ') or line_strip == ''):
                            playbook_lines.append(line)
                        # End of YAML block
                        elif yaml_start and not line.startswith(' ') and line_strip:
                            break

                    if playbook_lines and len(playbook_lines) > 2:
                        # Clean up the extracted YAML
                        yaml_content = '\n'.join(playbook_lines).strip()
                        result['playbook_content'] = yaml_content

                # If no proper YAML found, try to extract any shell commands
                if not result.get('playbook_content'):
                    # Look for shell commands that could be converted to Ansible
                    for line in lines:
                        if any(cmd in line.lower() for cmd in ['apt install', 'yum install', 'dnf install', 'systemctl', 'service']):
                            # Create simple Ansible playbook for the command
                            result['playbook_content'] = f"""---
- hosts: localhost
  become: yes
  tasks:
    - name: Execute command
      shell: {line.strip()}
"""
                            break

        except Exception as e:
            result['error'] = f"Failed to parse crew result: {e}"
            result['status'] = "error"

        return result
