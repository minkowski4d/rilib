# Work Instruction: Completing a Model Validation Report

## Purpose and Scope

This work instruction provides comprehensive guidance for preparing model validation reports in compliance with German banking regulations, specifically BaFin requirements and MaRisk AT 4.3.2. The instruction applies to all validators conducting independent validation of material risk models, including market risk models (such as Value-at-Risk and stress testing models), liquidity risk models (such as LCR and NSFR), and other quantitative models used for risk measurement and regulatory reporting.

Model validation reports serve as the primary documentation of the validation process and findings. These reports must be suitable for presentation to senior management, model risk committees, internal audit, and BaFin during supervisory inspections. The report structure follows a standardized format to ensure consistency across all model validations and to facilitate efficient review by stakeholders.

## Regulatory Context and Requirements

German banking regulation, particularly MaRisk AT 4.3.2, requires that all material models undergo independent validation at least annually. The validation must be conducted by qualified personnel who are organizationally independent from model development and implementation. The validation report serves as evidence of compliance with these requirements and must demonstrate that the validation was thorough, independent, and technically sound.

The European Banking Authority (EBA) guidelines on internal governance (EBA/GL/2019/01) further specify expectations for model validation. These guidelines emphasize the importance of comprehensive documentation, clear identification of model limitations and assumptions, and transparent communication of findings to senior management. Validation reports must be written in a manner that allows non-technical senior management to understand the key findings and their implications for risk management and business decisions.

BaFin's supervisory expectations emphasize conservative assumptions, comprehensive documentation, and clear articulation of model limitations. When preparing validation reports, validators should adopt a critical mindset and ensure that all potential issues are identified and communicated transparently. The report should not shy away from highlighting deficiencies, even if they are uncomfortable for model developers or users to address.

## Document Control and Identification

The validation report begins with completion of the document control section, which provides essential metadata about the validation. The model name is documented along with a unique model identifier that corresponds to the institution's model inventory system. This identifier ensures traceability and allows the report to be linked to the model's change history, previous validation reports, and ongoing monitoring activities.

The model type is classified clearly, specifying whether it is a market risk model, liquidity risk model, credit risk model, or another category. The model owner is identified, typically the business unit or department responsible for the model's use and maintenance. The model owner is accountable for addressing validation findings and ensuring the model remains fit for purpose.

The validation date and the validation period covered by the assessment are recorded. The validation date represents when the validation was completed, while the validation period indicates the timeframe of data and model performance reviewed during the validation. For example, a validation completed in January 2026 might cover model performance from January 2025 through December 2025.

All members of the validation team are documented, including their qualifications and roles. The lead validator is specified, who is responsible for overseeing the validation process and ensuring quality and completeness of the report. A version number is assigned to the report, indicating its status as either draft or final. Draft reports are shared with model owners for factual accuracy review and to obtain management responses to findings. Final reports incorporate these responses and are approved by appropriate governance bodies.

The distribution list for the report is specified, ensuring that it reaches all relevant stakeholders, including senior management, the model risk committee, internal audit, and BaFin (if requested during supervisory activities). Proper distribution ensures transparency and facilitates timely remediation of identified issues.

## Executive Summary

The executive summary provides a concise overview of the validation for senior management and other readers who may not review the entire report in detail. This section should be written last, after completing all other sections, to ensure it accurately reflects the validation findings and conclusions.

The section opens with a model overview that describes the model's purpose, methodology, and key use cases in no more than two paragraphs. This overview explains what the model does, how it is used in the business, and why it is important for risk management or regulatory compliance. For example, "The Value-at-Risk model uses historical simulation methodology to estimate the maximum potential loss on the trading portfolio at the 99% confidence level over a one-day holding period. The model is used daily for risk reporting to senior management, setting trading limits, and regulatory capital calculation under the internal models approach."

The validation scope is summarized in a single paragraph, highlighting the key validation activities performed. This summary explains what was validated and what was not, noting any limitations or constraints that affected the validation. For instance, "The validation covered conceptual soundness, data quality, implementation verification, backtesting results for the past 12 months, and outcomes analysis. The validation did not cover IT infrastructure or disaster recovery capabilities, which are assessed separately by the IT audit function."

The overall validation rating is stated prominently: Satisfactory, Satisfactory with Reservations, or Unsatisfactory. This rating represents the validator's overall judgment about whether the model is fit for its intended purpose. A "Satisfactory" rating indicates the model has no material deficiencies and can be used without restrictions. "Satisfactory with Reservations" means the model can be used but has identified issues that require remediation within specified timeframes or that certain conditions must be met. "Unsatisfactory" indicates the model has material deficiencies that prevent it from being used reliably for its intended purpose and requires immediate corrective action.

A summary table of key findings is provided, listing each finding with its unique identifier, severity level, brief description, and current status. Findings are categorized by severity: Critical findings have material impact on model outputs or decisions and require immediate action within one month. Major findings have significant impact and must be remediated within three months. Minor findings have limited impact and should be addressed within six months. Observations highlight enhancement opportunities but do not require mandatory remediation.

The executive summary concludes by listing any critical management actions required, along with specific timelines for completion. This ensures senior management understands their responsibilities and the urgency of addressing validation findings.

## Section 1: Model Description

The model description section establishes the foundation for the validation by comprehensively documenting what the model is, how it works, and how it is used. This section should be detailed enough that a qualified risk professional unfamiliar with the specific model can understand its essential features.

The model's primary purpose and all business use cases in which it is employed are described. This description explains whether the model is used for regulatory purposes such as ICAAP, ILAAP, or Pillar 3 reporting, and identifies the key business decisions that rely on model outputs. Understanding the model's intended use is critical because the validation must assess whether the model is appropriate for these purposes. For example, a model intended for daily risk management may not be suitable for stress testing under extreme scenarios without appropriate adjustments.

The model methodology is documented in technical detail, specifying the model type (such as VaR, Expected Shortfall, LCR, or pricing model) and the specific approach used (such as historical simulation, Monte Carlo simulation, parametric methods, or econometric forecasting). The key formulas and mathematical framework are described at a high level, ensuring that the description is sufficient for understanding the model's mechanics without overwhelming the reader with excessive technical detail. The time horizon (such as one-day holding period for VaR or 30-day projection for LCR) and the confidence level (such as 99% for VaR) are specified if applicable.

All key assumptions underlying the model are identified and analyzed. For each assumption, a clear description is provided, along with the justification or rationale for why the assumption is reasonable, and an assessment of the risk if the assumption is violated. Assumptions might include statistical properties of returns (such as independence or stationarity), behavioral patterns (such as deposit runoff rates), or market conditions (such as liquidity of certain instruments). The validator must critically assess whether these assumptions are appropriate for the model's intended use and whether they hold under stressed conditions.

All known limitations of the model are documented. Every model has limitations, and transparency about these limitations is essential for proper model risk management. For each limitation, its impact on model outputs is explained along with any mitigation measures in place. Limitations might include simplifying assumptions, data constraints, inability to capture certain risk factors, or computational constraints that prevent full revaluation of complex instruments. The model owner and users must understand these limitations to avoid misinterpreting model outputs or relying on the model beyond its capabilities.

Complete information about model governance is provided, including the model owner, model developer, approval authority (such as the model risk committee), and the date of the most recent approval. The model's classification in the institution's model inventory system is specified, typically using a tiered approach where Tier 1 models have the highest materiality and risk, requiring the most intensive validation. The required validation frequency is noted, which is typically annual for Tier 1 models but may be biennial for lower-tier models.

## Section 2: Validation Scope and Approach

This section explains what the validation aimed to achieve, how it was conducted, and any constraints that affected the validation process. Transparency about scope and methodology is essential for readers to understand the basis for the validation conclusions.

The validation objectives are stated clearly. Typically, the primary objective is to assess whether the model is fit for its intended purpose, but specific objectives may include evaluating model performance, assessing compliance with regulatory requirements, reviewing model changes since the last validation, or investigating specific concerns raised by model users or auditors.

The validation scope is delineated by specifying what was included and what was excluded from the validation. The scope should align with the model's materiality, complexity, and any changes since the last validation. For example, if a model underwent significant methodology changes, the validation should focus heavily on conceptual soundness and implementation verification. If the model has been stable but has experienced backtesting exceptions, the validation should emphasize ongoing monitoring and outcomes analysis. Clearly stating what is out of scope prevents misunderstandings about the validation's coverage and helps readers understand any limitations in the validation conclusions.

The validation methodology is described in sufficient detail that the validation could be replicated by another qualified validator. The validation approach, techniques used, and standards applied are explained. Relevant regulatory guidance, industry standards, or academic literature that informed the validation methodology are referenced. For example, "The backtesting approach follows the Basel Committee's framework for assessing VaR model accuracy, using the traffic light approach to evaluate the number of exceptions relative to the expected number at the 99% confidence level."

The data sources, data period, tools, and reference models used in the validation are documented. The origin of the data is specified, ensuring that the data is appropriate for validation purposes and, ideally, sourced independently from the data used in model development. The time period covered by the data is stated, which should be sufficient to assess model performance under various market conditions. The tools employed are listed, such as Python, R, Excel, or specialized statistical software. If benchmark or reference models were used for comparison, they are described along with explanation of why they provide a meaningful comparison to the model being validated.

Information about the validation team is provided along with confirmation of their independence from model development and implementation. Independence is a regulatory requirement and is essential for maintaining objectivity and credibility. The lead validator's name and qualifications are stated, along with the names of other team members. A clear independence statement is included confirming that none of the team members were involved in developing, implementing, or using the model, and that the team reports to a function independent of the model owner.

Any limitations of the validation process itself are acknowledged. No validation can cover every possible scenario or address every conceivable concern. Limitations might include data availability constraints, time or resource constraints, limitations of validation tools or techniques, or inability to access certain systems or documentation. Being transparent about validation limitations demonstrates professional integrity and helps readers interpret the validation conclusions appropriately.

## Section 3: Conceptual Soundness Review

The conceptual soundness review assesses whether the model's theoretical and methodological foundations are appropriate for its intended use. This is a critical validation area because a fundamentally flawed methodology cannot be salvaged through implementation excellence or data quality improvements.

The theoretical framework is assessed by evaluating whether the model is based on sound economic, financial, or statistical principles. The relevant academic literature and industry practices are reviewed to determine whether the chosen methodology is well-established and appropriate for the model's purpose. For example, historical simulation is an appropriate methodology for VaR calculation for liquid portfolios with sufficient historical data, but may be inadequate for portfolios with significant optionality or positions in illiquid instruments. A rating (Satisfactory, Needs Improvement, or Unsatisfactory) is assigned based on this assessment and detailed analysis is provided to support the rating.

Each assumption underlying the model is analyzed, assessing whether it is reasonable, supported by empirical evidence, and appropriate for the model's use cases. For each assumption, it is classified as reasonable, questionable, or invalid. If assumptions are questionable, the concerns are explained and whether they materially affect model reliability is assessed. If assumptions are invalid, these represent critical findings that must be addressed immediately. Specific comments are provided on each assumption, citing relevant data, research, or experience that informs the assessment.

Whether the methodology is appropriate for the model's intended purpose is evaluated. A methodology may be theoretically sound in general but inappropriate for a specific application. For example, a parametric VaR approach assuming normal distribution may be conceptually sound for simple portfolios but inappropriate for portfolios with significant tail risk. Consideration is given to whether the methodology adequately captures the key risks the model is intended to measure and whether it provides outputs that are meaningful for the business decisions it supports.

The model's compliance with relevant regulatory requirements is assessed, including MaRisk AT 4.3.2, EBA guidelines on internal governance and internal models, and CRR/CRD IV requirements for capital adequacy. Whether the model meets each applicable requirement is specified and any gaps or areas where compliance is unclear are identified. Regulatory compliance is not merely a box-checking exercise; it reflects the regulator's expectations for robust and reliable risk measurement.

The model is compared with industry benchmarks, peer models, and alternative methodologies. This comparison provides context for assessing whether the institution's model is consistent with industry practice or represents an outlier approach. If the model differs significantly from standard industry practice, whether there is a compelling justification for the difference or whether it represents a deficiency is evaluated. Any alternative methodologies that might be more appropriate or that could serve as useful complements or cross-checks to the current model are noted.

All findings related to conceptual soundness are summarized, providing clear references to where each finding is documented in detail in Section 8. Each finding should be assigned a unique identifier, severity level, and clear description.

## Section 4: Data Quality Assessment

Data quality is foundational to model reliability. A well-designed model implemented correctly will still produce unreliable outputs if the input data is incomplete, inaccurate, or inappropriate. The data quality assessment evaluates whether the model's data inputs meet the standards necessary for reliable risk measurement.

Each data source used by the model is evaluated, assessing its quality, reliability, and appropriateness for the model's purpose. Factors such as the reputation and reliability of the data provider, the timeliness and frequency of data updates, the consistency of data over time, and the alignment between the data and the risk factors the model is intended to measure are considered. A quality rating is assigned to each data source and any issues that affect data reliability are identified. This information is presented in a structured format that facilitates easy review and comparison across data sources.

Data completeness is analyzed by quantifying the rate of missing data and identifying any gaps in time series. Missing data can introduce bias if it is systematically related to market conditions or portfolio characteristics. For example, if market data is missing on days of extreme volatility, the model may underestimate risk. How missing data is treated by the model, such as through interpolation, omission, or substitution with proxy data, is assessed. Whether the treatment is appropriate and whether the rate of missing data is acceptable given the model's purpose is evaluated.

Data accuracy is verified through reconciliation with alternative sources, cross-checks against market data providers, or comparison with regulatory reporting data. Any discrepancies are identified and their causes investigated. Material data errors can significantly distort model outputs, so this is a critical validation activity. The procedures used for data accuracy verification and the results obtained are documented.

Whether the historical data available is adequate for the model's methodology is assessed. Many models, such as historical simulation VaR or econometric forecasting models, require a substantial history of data to produce reliable estimates. The data history required based on the model's methodology and risk factors is specified, and this is compared to the data history actually available. If the available history is insufficient, this represents a significant limitation that may affect model reliability, particularly during periods of market stress or regime changes.

All data transformation processes are reviewed, including data cleansing, filtering, aggregation, and adjustment procedures. Whether these transformations are appropriate, well-documented, and implemented correctly is ensured. Inappropriate data transformations can introduce errors or bias. For example, excessive smoothing of time series data may mask volatility, while inappropriate aggregation methods may fail to capture important risk characteristics.

All findings related to data quality are summarized, ensuring each finding is clearly described and linked to its detailed documentation in Section 8.

## Section 5: Implementation Review

The implementation review assesses whether the model is implemented correctly in production systems and whether appropriate controls are in place to ensure ongoing implementation integrity. Even a conceptually sound model with high-quality data will produce unreliable results if the implementation contains errors or lacks adequate controls.

A code review is conducted to assess the quality, structure, documentation, and maintainability of the model's implementation. The programming logic is reviewed to ensure it aligns with the model methodology documentation. Common coding errors, inefficient algorithms, or hard-coded parameters that should be configurable are checked for. Whether the code is well-structured with clear comments and documentation that would allow another developer to understand and maintain it is assessed. A rating is assigned based on the overall code quality and any concerns about code structure, complexity, or documentation are documented.

Model calculations are verified by independently recalculating model outputs for a representative set of test cases. The validation team's results are compared with the model's production outputs to ensure they match within acceptable tolerance. Discrepancies indicate potential implementation errors that must be investigated and resolved. All test cases used, the expected results, the actual results produced by the model, whether they match, and any explanatory comments are documented. Testing should cover normal conditions, boundary conditions, and edge cases to ensure the model performs correctly across its entire operating range.

System integration is assessed by reviewing how data flows into the model from source systems, how the model interfaces with other systems, and how outputs are transmitted to downstream users and systems. Whether these interfaces are robust, well-controlled, and properly documented is evaluated. Integration issues are a common source of operational risk and can lead to errors in production use even if the core model is sound.

The control environment surrounding the model is reviewed, including manual controls (such as user review of outputs), automated controls (such as data quality checks or reasonableness tests on outputs), reconciliation processes, and four-eyes principles (such as independent review of key inputs or parameter changes). A strong control environment reduces the risk of undetected errors and provides assurance that issues will be identified and addressed promptly.

Change management processes are assessed, including how model changes are documented, tested, and approved before implementation in production. Version control practices, the adequacy of testing procedures, and the documentation of changes are reviewed. Strong change management ensures that changes do not inadvertently introduce errors and that there is a clear audit trail of model evolution over time.

Documentation quality is evaluated by assessing the availability and quality of key model documents, including the methodology document, user guide, technical specification, and prior validation reports. Each document type serves a specific purpose in supporting model understanding, appropriate use, and governance. The availability and quality of each document type are rated and comments on any deficiencies are provided. Inadequate documentation increases model risk by making it difficult for users to understand the model's capabilities and limitations, for validators to assess the model, or for auditors to evaluate model governance.

All findings related to implementation are summarized, with each finding clearly identified and linked to its detailed documentation in Section 8.

## Section 6: Ongoing Monitoring Review

Ongoing monitoring involves tracking model performance over time to identify any degradation in accuracy, changes in risk profile, or other issues that may indicate the model is no longer performing as intended. This section reviews whether ongoing monitoring activities are adequate and whether model performance has been satisfactory.

The performance metrics that are tracked regularly for the model are analyzed. These might include forecast accuracy metrics, error rates, the stability of model parameters or outputs, or the frequency of exceptions or overrides. Whether the defined metrics are appropriate for identifying potential issues and whether they are monitored with sufficient frequency is assessed. A rating is assigned based on whether performance monitoring is satisfactory and any concerns about the adequacy of ongoing monitoring activities are documented.

For market risk models, particularly VaR and Expected Shortfall models, backtesting results are reviewed comprehensively. Backtesting compares the model's risk estimates to actual losses to assess whether the model is accurately calibrated. The Basel Committee's traffic light approach provides a framework for evaluating backtesting results: green zone indicates satisfactory performance, yellow zone suggests potential issues requiring investigation, and red zone indicates serious concerns requiring immediate action. Backtesting results are analyzed over multiple periods, any exceptions (cases where actual losses exceeded the VaR estimate) are identified, and the number of exceptions is compared to the expected number based on the confidence level. Whether exceptions cluster in time (suggesting model weakness during certain market conditions) or are randomly distributed is assessed. The traffic light classification for each period is documented and a comprehensive assessment of backtesting performance is provided.

For liquidity risk models, particularly LCR and NSFR models, coverage ratios and trends over time are analyzed. Whether the model produces stable and reasonable estimates and whether the coverage ratios meet regulatory requirements with adequate buffer is evaluated. Any significant fluctuations or trends are identified and whether they reflect genuine changes in the institution's liquidity position or potential model issues is assessed.

Model outputs are compared with relevant benchmarks, such as market data, peer institution reports, alternative models, or simplified approaches. Benchmark comparison provides perspective on whether model outputs are reasonable and consistent with external reference points. Material deviations from benchmarks require investigation to determine whether they reflect unique characteristics of the institution or potential model deficiencies.

Model stability is assessed by analyzing whether model parameters and outputs remain stable over time or whether there is evidence of instability or drift. While some parameters should evolve as market conditions change, excessive instability may indicate specification problems, data issues, or inadequate calibration procedures. Significant changes in outputs that are not explainable by changes in risk profile or market conditions also warrant investigation.

Exceptions and breaches are reviewed, including instances where model outputs were overridden by management judgment, cases where outputs triggered pre-defined limits or alerts, or situations where the model produced implausible results. The frequency and nature of such exceptions are analyzed to assess whether they indicate systematic model weaknesses or are isolated incidents. Excessive reliance on overrides suggests the model is not adequately capturing risk and may need enhancement.

All findings related to ongoing monitoring are summarized, with each finding clearly identified and linked to its detailed documentation in Section 8.

## Section 7: Outcomes Analysis

Outcomes analysis evaluates whether model outputs are reasonable, explainable, and appropriate for supporting the business decisions for which the model is used. This section assesses the model's outputs from a practical business perspective, complementing the technical assessments in earlier sections.

Output reasonableness is assessed by evaluating whether model outputs are plausible, consistent with expectations, and explainable. Outputs are compared to prior periods, alternative approaches, and qualitative expectations based on market conditions and portfolio characteristics. Any outputs that appear anomalous or counterintuitive are identified and the causes investigated. Model outputs that cannot be explained or that contradict knowledgeable judgment warrant investigation. A rating is assigned based on whether outputs are consistently reasonable and well-explained.

Sensitivity analysis is conducted to assess how model outputs change in response to variations in key inputs and parameters. Sensitivity analysis reveals which inputs have the most significant influence on outputs and helps assess whether the model's sensitivity is appropriate. For example, a VaR model should be sensitive to changes in volatility and correlations, but excessive sensitivity to minor data variations may indicate instability. The sensitivity analysis is documented in a structured format showing the base case, stressed scenarios, the resulting output change, and an assessment of whether the sensitivity is appropriate. This analysis should cover a range of scenarios, including both plausible market movements and more extreme stress conditions.

Scenario analysis is performed by running the model under alternative assumptions or historical stress scenarios to assess whether it produces reasonable results under a variety of conditions. Scenario analysis helps identify potential weaknesses that may not be apparent under normal market conditions. For example, a model that performs well in stable markets but breaks down under stress may be inadequate for risk management purposes. The scenarios tested, the results obtained, and the implications for model reliability are documented.

Comparative analysis is conducted by comparing model outputs with alternative methodologies, simplified approaches, or peer models. Differences are not necessarily problematic, but material differences should be investigated and explained. If a simplified approach produces substantially different results, understanding the source of the difference provides insight into the model's behavior and whether its complexity is justified. If peer institutions report substantially different risk measures for similar portfolios, this may indicate potential issues with the model or differences in risk profile that should be understood.

The business impact of model outputs is assessed by analyzing how they influence business decisions, capital allocation, risk appetite, limit setting, or other key management activities. Whether decision-makers understand and appropriately use model outputs and whether the model provides timely and actionable information is evaluated. Even a technically sound model provides limited value if its outputs are not used effectively in business decision-making. Any instances where model outputs appear to be ignored or systematically overridden are identified, as this may indicate that the model is not well-suited to its intended purpose.

All findings related to outcomes analysis are summarized, with each finding clearly identified and linked to its detailed documentation in Section 8.

## Section 8: Findings and Recommendations

The findings and recommendations section is the core of the validation report. It documents every issue identified during the validation, organized by severity level, and provides specific recommendations for remediation. This section must be comprehensive, clear, and actionable.

Findings are organized into four categories based on severity: Critical, Major, Minor, and Observations. Critical findings have material impact on model outputs or business decisions and require immediate action, typically within one month. Examples include fundamental flaws in methodology, material data errors, or implementation bugs that significantly distort outputs. Major findings have significant impact but do not immediately compromise the model's usability; these require remediation within three months. Minor findings have limited impact and should be addressed within six months. Observations identify enhancement opportunities or best practices but do not require mandatory remediation.

For each finding, a unique identifier is assigned using a consistent naming convention (such as F-001, F-002 for findings and O-001, O-002 for observations). The severity level is specified and which validation area the finding relates to is identified (Conceptual Soundness, Data Quality, Implementation, Ongoing Monitoring, or Outcomes Analysis).

A detailed description of each finding is provided, explaining what the issue is, how it was identified, and why it is a concern. The description should be sufficiently detailed that the model owner clearly understands the issue and can take appropriate corrective action. Vague statements are avoided; instead, specific examples, data, or evidence supporting the finding are provided.

The impact of each finding on model outputs, risk measurement accuracy, business decisions, or regulatory compliance is assessed and documented. The impact is quantified where possible. Understanding the impact helps prioritize remediation efforts and ensures that model owners and senior management appreciate the significance of addressing the finding.

A specific, actionable recommendation for addressing each finding is provided. Recommendations should be concrete rather than generic. For example, instead of "improve data quality," the recommendation might be "implement automated reconciliation between the market data feed and the front office pricing system, with daily exception reporting to identify discrepancies within one business day." Clear recommendations facilitate prompt and effective remediation.

Space is included for the model owner to provide a management response to each finding. The management response should indicate whether the model owner agrees with the finding, outline the planned remediation approach, and commit to a target completion date. Management responses are typically obtained during the draft report review process and incorporated into the final report. This process ensures accountability and facilitates tracking of remediation progress.

The target completion date for addressing each finding is specified, based on its severity level. Critical findings should be addressed within one month, major findings within three months, and minor findings within six months. In some cases, interim mitigating actions may be implemented more quickly while longer-term solutions are developed.

Findings are presented in a professional, objective manner that clearly communicates concerns without being unnecessarily critical or inflammatory. The goal is to improve model quality, not to assign blame. The focus is on facts, evidence, and the implications for model risk management.

## Section 9: Validation Conclusion

The validation conclusion synthesizes the results of all validation activities and provides the validator's overall judgment about the model's fitness for purpose. This section should be concise but comprehensive, ensuring that readers understand the validation's bottom-line conclusions.

An overall assessment is provided that integrates findings from all validation areas. The model's strengths and weaknesses are discussed in a balanced manner. What the model does well is acknowledged while being transparent about limitations and areas requiring improvement. The assessment should be comprehensive enough that a reader who skips the detailed sections can still understand the key messages about model quality and reliability.

The overall validation rating is stated clearly and detailed justification for the rating is provided. If the rating is "Satisfactory," why the validator has confidence the model is fit for purpose despite any minor findings is explained. If the rating is "Satisfactory with Reservations," what the reservations are and what conditions must be met for the model to be used reliably are specified. If the rating is "Unsatisfactory," why the model cannot be relied upon in its current state and what fundamental changes are needed are explained.

A fitness for purpose statement is provided that explicitly addresses whether the model is suitable for its intended use cases. For example, "Based on the validation findings, the VaR model is fit for purpose for daily risk reporting and setting trading limits, provided that the critical and major findings are addressed within the specified timeframes. However, the model should not be used for regulatory capital calculations under the internal models approach until the data quality and backtesting issues documented in findings F-001 and F-003 are resolved."

Any conditions for use that must be observed to ensure the model is used appropriately given its limitations are documented. Conditions might include restricting the model to specific use cases, requiring additional review or judgment for certain outputs, or implementing enhanced monitoring until identified issues are remediated. These conditions provide important guidance to model users and help manage model risk during the remediation period.

When the next validation is due is specified, typically based on the institution's validation policy and the model's classification. Any circumstances that would trigger an earlier validation are noted, such as material methodology changes, significant changes in the risk profile of portfolios covered by the model, persistent backtesting exceptions, or changes in regulatory requirements. These triggers ensure that validation frequency is appropriately responsive to model risk.

## Section 10: Appendices

The appendices provide detailed technical analysis, test results, and supporting documentation that would be too voluminous or detailed to include in the main body of the report. Readers seeking deeper understanding of specific technical issues can refer to the appendices for additional detail.

Appendix A contains detailed technical analysis, including complex calculations, statistical tests, or in-depth examination of methodological issues. This might include sensitivity analysis calculations, statistical tests of model assumptions, or detailed comparison of model outputs with benchmark models. The main report should summarize key results, while the appendix provides the full technical detail.

Appendix B contains test results and evidence, including detailed test cases, screenshots of system outputs, data files used in validation, or output files from validation analyses. This appendix serves as the audit trail demonstrating that the validation activities described in the main report were actually performed.

Appendix C provides a data dictionary defining all data fields used by the model. This reference is valuable for understanding exactly what data the model consumes and how it is defined, structured, and sourced.

Appendix D includes worked examples of key calculations, showing step-by-step how the model processes inputs to produce outputs. Calculation examples are particularly valuable for complex models where the methodology document may provide formulas but not show how they are applied in practice.

Appendix E lists all references cited in the validation report, including regulatory guidance, EBA guidelines, academic papers, industry standards, and internal documents. Proper referencing demonstrates that the validation is grounded in recognized standards and best practices.

Appendix F provides a glossary of acronyms and definitions. Given the extensive use of regulatory and technical terminology in validation reports, a comprehensive glossary ensures that all readers, including senior management and audit, can understand the terminology used throughout the report. Both German and English terms are included where appropriate, given that BaFin documentation may require German terminology while internal discussions may use English.

## Document Review and Approval

The validation report is completed by obtaining appropriate reviews and approvals. The validation process typically includes a factual accuracy review by the model owner, during which the model owner can identify any factual errors in the report and provide management responses to findings. After incorporating the model owner's feedback, the report should be reviewed and approved by the lead validator, the validation manager (who oversees the validation function), and ultimately by senior management or the model risk committee.

The approval table documents who reviewed and approved the report and when. This provides accountability and demonstrates appropriate governance of the validation process. Signatures (or electronic approval records) should be retained according to the institution's document retention policies to support regulatory inspections and internal audits.

Once approved, the final validation report should be distributed to all stakeholders, filed in the model's official record, and tracked for follow-up on findings remediation. The validation is not complete until all findings have been addressed or formally accepted as limitations to be managed through controls and conditions of use.

## Quality Control and Best Practices

Throughout the validation report preparation process, high standards of quality, clarity, and professionalism should be maintained. The report should be well-organized, clearly written, and free from grammatical errors or typographical mistakes. Consistent terminology and formatting should be used throughout. Tables, charts, and figures should be clearly labeled and referenced in the text.

The report should be written for the intended audience, recognizing that validation reports are read by diverse stakeholders with varying levels of technical expertise. Technical detail is important, but it should be presented in a manner that allows non-technical readers to understand the key messages. The main report should be used for high-level findings and implications, while detailed technical analysis should be relegated to appendices.

All assessments should be objective and evidence-based. Validation conclusions should be supported by data, analysis, and logical reasoning, not by unsupported opinion. If professional judgment is required (as it often is), the basis for that judgment should be explained.

Independence should be maintained throughout the validation process and the report should reflect the validator's independent judgment, not the preferences of model owners or users. Independence is critical to the credibility of the validation function and to meeting regulatory requirements.

The validation process should be documented thoroughly, maintaining working papers, analysis files, and correspondence that support the validation report. These materials serve as the audit trail and may be reviewed by internal audit, external audit, or BaFin during supervisory activities.

Finally, timely completion of the validation report should be ensured. Delays in validation reduce its value and may result in models being used longer than appropriate without independent assessment. Clear timelines should be established at the start of the validation and proactive communication with stakeholders should occur if issues arise that may affect timing.

By following this work instruction, validators will produce high-quality validation reports that meet regulatory requirements, effectively communicate findings to stakeholders, and support sound model risk management within the institution.
