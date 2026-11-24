using Avalonia.Controls;
using Avalonia.Interactivity;

namespace TrendAlgo.Shell.Views;

public partial class GlossaryPopupWindow : Window
{
    public GlossaryPopupWindow()
    {
        InitializeComponent();
    }

    public void Bind(string title, string category, string body, string? formula = null, string? formulaLabel = null)
    {
        Title = string.IsNullOrWhiteSpace(title) ? "Glossary" : $"Glossary — {title}";
        TitleText.Text = string.IsNullOrWhiteSpace(title) ? "Glossary" : title;
        CategoryText.Text = string.IsNullOrWhiteSpace(category) ? "TA glossary" : category;
        BodyText.Text = string.IsNullOrWhiteSpace(body) ? "No glossary entry for this term yet." : body;
        var hasFormula = !string.IsNullOrWhiteSpace(formula);
        FormulaPanel.IsVisible = hasFormula;
        if (hasFormula)
        {
            FormulaHeading.Text = string.IsNullOrWhiteSpace(formulaLabel) ? "Formula" : formulaLabel;
            FormulaText.Text = formula;
        }
    }

    private void OnClose(object? sender, RoutedEventArgs e) => Close();
}
