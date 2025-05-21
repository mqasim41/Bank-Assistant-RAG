import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .logger import setup_logger

# Set up logger for this module
logger = setup_logger("bank_llm.guardrails", "guardrails.log")

@dataclass
class PolicyViolation:
    type: str
    description: str
    severity: str  # 'low', 'medium', 'high'
    context: Optional[str] = None

class ContentGuardrails:
    def __init__(self):
        # Sensitive information patterns
        self.patterns = {
            'credit_card': r'(?:\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b)',
            'ssn': r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            'phone': r'\b(?:\+\d{1,3}[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'account_number': r'\b\d{10,17}\b',
            'routing_number': r'\b\d{9}\b',
            'swift_code': r'\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b',
            'iban': r'\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b',
        }

        # Compile all patterns
        self.pattern_regex = re.compile('|'.join(f'(?P<{k}>{v})' for k, v in self.patterns.items()), flags=re.I)

        # Restricted keywords and phrases
        self.restricted_keywords = {
            'high_severity': [
                'password', 'pin', 'secret', 'token', 'key', 'credential',
                'social security', 'ssn', 'tax id', 'ein', 'itin',
                'routing number', 'swift code', 'iban', 'account number'
            ],
            'medium_severity': [
                'salary', 'income', 'revenue', 'profit', 'loss',
                'balance', 'statement', 'transaction', 'transfer',
                'withdraw', 'deposit', 'loan', 'mortgage'
            ],
            'low_severity': [
                'bank', 'branch', 'atm', 'card', 'account',
                'customer', 'client', 'user', 'member'
            ]
        }

        # Offensive language patterns
        self.offensive_patterns = {
            'high_severity': [
                r'\b(?:n[-\s]?i[-\s]?g[-\s]?g[-\s]?e[-\s]?r|f[-\s]?a[-\s]?g[-\s]?g[-\s]?o[-\s]?t|k[-\s]?i[-\s]?k[-\s]?e|s[-\s]?p[-\s]?i[-\s]?c|w[-\s]?o[-\s]?p|g[-\s]?o[-\s]?o[-\s]?k|s[-\s]?l[-\s]?o[-\s]?p|d[-\s]?y[-\s]?k[-\s]?e|t[-\s]?w[-\s]?a[-\s]?t|g[-\s]?r[-\s]?e[-\s]?a[-\s]?s[-\s]?e[-\s]?r|s[-\s]?p[-\s]?a[-\s]?z|r[-\s]?e[-\s]?t[-\s]?a[-\s]?r[-\s]?d|m[-\s]?o[-\s]?r[-\s]?o[-\s]?n|i[-\s]?d[-\s]?i[-\s]?o[-\s]?t)\b',
                r'\b(?:f[-\s]?u[-\s]?c[-\s]?k|s[-\s]?h[-\s]?i[-\s]?t|a[-\s]?s[-\s]?s|b[-\s]?i[-\s]?t[-\s]?c[-\s]?h|c[-\s]?u[-\s]?n[-\s]?t|d[-\s]?i[-\s]?c[-\s]?k|p[-\s]?u[-\s]?s[-\s]?s[-\s]?y|t[-\s]?i[-\s]?t|w[-\s]?h[-\s]?o[-\s]?r[-\s]?e)\b'
            ]
        }

        # Compile keyword patterns
        self.keyword_patterns = {
            severity: re.compile('|'.join(f'\\b{kw}\\b' for kw in keywords), re.I)
            for severity, keywords in self.restricted_keywords.items()
        }

        # Compile offensive patterns
        self.offensive_regex = re.compile('|'.join(self.offensive_patterns['high_severity']), re.I)

        logger.info("ContentGuardrails initialized with security patterns and policies")

    def check_sensitive_info(self, text: str) -> List[PolicyViolation]:
        """Check for sensitive information patterns in text."""
        violations = []
        
        # Check for PII patterns
        for match in self.pattern_regex.finditer(text):
            pii_type = match.lastgroup
            context = text[max(0, match.start()-20):min(len(text), match.end()+20)]
            violations.append(PolicyViolation(
                type='sensitive_info',
                description=f'Detected {pii_type}',
                severity='high',
                context=context
            ))
            logger.warning(f"Detected sensitive information ({pii_type}) in text")

        return violations

    def check_restricted_keywords(self, text: str) -> List[PolicyViolation]:
        """Check for restricted keywords and phrases."""
        violations = []
        
        for severity, pattern in self.keyword_patterns.items():
            for match in pattern.finditer(text):
                context = text[max(0, match.start()-20):min(len(text), match.end()+20)]
                violations.append(PolicyViolation(
                    type='restricted_keyword',
                    description=f'Found restricted keyword: {match.group()}',
                    severity=severity,
                    context=context
                ))
                logger.info(f"Detected {severity} severity keyword: {match.group()}")

        return violations

    def check_content_length(self, text: str) -> List[PolicyViolation]:
        """Check if content length is within acceptable limits."""
        violations = []
        
        if len(text) > 10000:  # 10k characters
            violations.append(PolicyViolation(
                type='content_length',
                description='Content exceeds maximum length',
                severity='medium'
            ))
            logger.warning("Content length exceeds maximum limit")
        
        return violations

    def check_offensive_language(self, text: str) -> List[PolicyViolation]:
        """Check for offensive language and slurs in text."""
        violations = []
        
        for match in self.offensive_regex.finditer(text):
            context = text[max(0, match.start()-20):min(len(text), match.end()+20)]
            violations.append(PolicyViolation(
                type='offensive_language',
                description='Detected offensive language or slur',
                severity='high',
                context=context
            ))
            logger.warning("Detected offensive language in text")

        return violations

    def enforce_policies(self, text: str) -> tuple[str, List[PolicyViolation]]:
        """
        Enforce all content policies and return sanitized text with violations.
        """
        if not isinstance(text, str):
            logger.error("Received non-string input for policy enforcement")
            return "", [PolicyViolation(
                type='invalid_input',
                description='Input must be a string',
                severity='high'
            )]

        # Collect all violations
        violations = []
        violations.extend(self.check_sensitive_info(text))
        violations.extend(self.check_restricted_keywords(text))
        violations.extend(self.check_content_length(text))
        violations.extend(self.check_offensive_language(text))

        # Sanitize text based on violations
        sanitized_text = text
        for violation in violations:
            if violation.type == 'sensitive_info':
                # Redact sensitive information
                sanitized_text = self.pattern_regex.sub('[REDACTED]', sanitized_text)
            elif violation.type == 'restricted_keyword' and violation.severity == 'high':
                # Redact high-severity keywords
                sanitized_text = self.keyword_patterns['high_severity'].sub('[REDACTED]', sanitized_text)
            elif violation.type == 'offensive_language':
                # Redact offensive language
                sanitized_text = self.offensive_regex.sub('[REDACTED]', sanitized_text)

        # Log summary of violations
        if violations:
            logger.info(f"Found {len(violations)} policy violations in text")
            for v in violations:
                logger.debug(f"Violation: {v.type} - {v.description} ({v.severity})")

        return sanitized_text, violations

# Create singleton instance
guardrails = ContentGuardrails()

def enforce_policies(text: str) -> str:
    """
    Main entry point for policy enforcement.
    Returns sanitized text with sensitive information redacted.
    """
    sanitized_text, violations = guardrails.enforce_policies(text)
    return sanitized_text
