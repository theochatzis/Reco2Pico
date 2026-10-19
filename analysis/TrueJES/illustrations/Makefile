# TikZ illustrations of the TrueJES study. `make` builds every figure (cropped
# PDFs via the preview package) and the summary document; `make clean` removes
# the LaTeX by-products.
FIGS = ladder ancestry_matching entrance_rule calo_deposits reco_attribution attribution_chain pileup_attribution attribution_samples pileup_truth pf_block
PDFS = $(addsuffix .pdf,$(FIGS))
all: $(PDFS) TrueJES_illustrations.pdf
%.pdf: %.tex preamble.tex
	pdflatex -interaction=nonstopmode -halt-on-error $< > $*.log.txt 2>&1 || (tail -30 $*.log.txt; false)
TrueJES_illustrations.pdf: TrueJES_illustrations.tex $(PDFS)
	pdflatex -interaction=nonstopmode -halt-on-error $< > TrueJES_illustrations.log.txt 2>&1 || (tail -30 TrueJES_illustrations.log.txt; false)
	pdflatex -interaction=nonstopmode -halt-on-error $< > /dev/null 2>&1
clean:
	rm -f *.aux *.log *.log.txt *.out
.PHONY: all clean
